import datetime
import inspect
import json
import re
from enum import Enum
from io import BytesIO

import django.conf
import urllib3
from commercetools import CommercetoolsError
from commercetools.importapi import Client
from commercetools.importapi.models import AssetDimensions, AttributeConstraintEnum, \
    AttributeDefinition, AttributeType, \
    Image, LocalizableTextAttribute, LocalizedString, \
    MoneyType, PriceDraftImport, ProductDraftImport, \
    ProductTypeImport, ProductTypeKeyReference, \
    ProductVariantDraftImport, TextAttribute, TypedMoney
# noinspection PyProtectedMember
from commercetools.importapi.models.importcontainers import ImportContainerDraft, ImportResourceType
from commercetools.importapi.models.importrequests import ProductDraftImportRequest, ProductTypeImportRequest
from commercetools.importapi.models.producttypes import TextInputHint
from dateutil import parser as dateparser
from django.core.management.base import no_translations
from PIL import Image as PILImage

from commerce_coordinator.apps.commercetools.management.commands._timed_command import TimedCommand

# Notes on 'keys':
#   - Keys may only contain alphanumeric characters, underscores and hyphens and must have a minimum length of
#     2 characters and maximum length of 256 characters.
#   - I am attempting to make a standard naming convention:
#       <line_of_business>-<system_local_identifier>
#
#     I see the Lines of business as follows:
#       - 2u: Company-wide/Global
#       - edx: edX
#       - gs: GetSmarter
#       - mm: MicroMasters

# TODO: Paginate?
# TODO: Split between 180,000 items (limit is 200,000 but i like margins for error)

# ##  ssh grmartin@theseus.sandbox.edx.org -L 9200:127.0.0.1:9200

DISCO_DEBUG_ES = True
DISCO_MAX_PER_PAGE = 10
COMMTOOLS_MAX_PER_BATCH = 180000


class DiscoIndex(Enum):
    COURSES = 'course'
    COURSE_RUNS = 'course_run'
    PROGRAMS = 'program'
    LEARNER_PATHWAYS = 'learner_pathway'
    PEOPLE = 'person'


class IdentifierProtection:
    """
    This class validates that automated identifiers are 'ok' according to various CT Rules as well as tries to apply
        a per-run sanity check on identifier reuse
    """

    FAILURE_IS_FATAL = True

    # this might need to be SQLite or something long term... but for now, in mem.
    key_name_inventory = []
    slug_inventory = []
    sku_inventory = []

    @staticmethod
    def fail_if_needed(message='Validation failed', force=False):
        print(f'*** ERROR [Internal Script Validation]: {message}')

        if force or IdentifierProtection.FAILURE_IS_FATAL:
            exit(999)

    @staticmethod
    def must_prefix(x: str):
        if x is None:
            IdentifierProtection.fail_if_needed(f"The key/name/slug of {x} is null prefixed properly.", force=True)

        if not x.startswith('edx-'):
            IdentifierProtection.fail_if_needed(f"The key/name/slug of {x} was not prefixed properly.", force=True)

    def key_or_name(self, key):
        self.must_prefix(key)

        if key in self.key_name_inventory:
            self.fail_if_needed(f"The key/name {key} is being reused.")

        if not re.match('^[A-Za-z0-9_-]{2,256}$', key):
            self.fail_if_needed(f"The key/name {key} is not valid.")

        self.key_name_inventory.append(key)

        return key

    def sku(self, sku):
        self.must_prefix(sku)

        if sku in self.sku_inventory:
            self.fail_if_needed(f"The key/name {sku} is being reused.")

        self.sku_inventory.append(sku)

        return sku

    def slug(self, slug):
        self.must_prefix(slug)

        if slug in self.slug_inventory:
            self.fail_if_needed(f"The slug {slug} is being reused.")

        if not re.match('^[a-zA-Z0-9_-]{2,256}$', slug):
            self.fail_if_needed(f"The slug {slug} is not valid.")

        self.slug_inventory.append(slug)

        return slug


class KeyGen:
    """
    Normalizes Keys, Names and Slugs for edX Products and Items

    - `Keys` shouldn't ever be prefixed the same to prevent overlaps which will mess up imports as they must be unique
      across the Project and may only contain alphanumeric characters, underscores and hyphens and must have a
      minimum length of 2 characters and maximum length of 256 characters. (must match ^[A-Za-z0-9_-]+$)
    - `Slugs` must be unique across a Project, but a product can have the same slug for different languages.
      Allowed characters are alphabetic, numeric, underscore (_) and hyphen (-) characters.
    - `Names` are User-defined name of the Attribute that is unique within the Project, and have a
      minimum length of 2 characters and maximum length of 256 characters and must match: ^[A-Za-z0-9_-]+$
    """

    check = IdentifierProtection()

    @staticmethod
    def import_container(name):
        return KeyGen.check.key_or_name(f"edx-container-{name}")  # key

    @staticmethod
    def product(uuid):
        return KeyGen.check.key_or_name(f"edx-prod-{uuid}")  # key

    @staticmethod
    def product_slug(uuid):
        return KeyGen.check.slug(f"edx-{uuid}")  # slug

    @staticmethod
    def product_variant(slug):
        return KeyGen.check.key_or_name(f"edx-var-{slug}")  # key

    @staticmethod
    def product_variant_attribute(name):
        return KeyGen.check.key_or_name(f"edx-{name}")  # name

    @staticmethod
    def product_type(name):
        return KeyGen.check.key_or_name(f"edx-{name}")  # key

    @staticmethod
    def product_variant_price(sku):
        return KeyGen.check.key_or_name(f"edx-usd_price-{sku}")  # key

    @staticmethod
    def sku(sku):
        return KeyGen.check.key_or_name(f"edx-sku-{sku}")  # sku


def ls(string_dict) -> LocalizedString:  # forced return typehint/coercion intentional to avoid bad IDE warnings
    """ Make a LocalizedString that doesn't freak out type checking, assign en to en-US as well. """
    if 'en' in string_dict:
        # Keys are CASE sensitive. String matching the pattern ^[a-z]{2}(-[A-Z]{2})?$ representing an IETF language tag
        string_dict['en-US'] = string_dict['en']

    return string_dict


def is_date_between(subject: datetime, start: datetime, end: datetime):
    # You have convert TZ or else you may hit: TypeError: can't compare offset-naive and offset-aware datetimes
    return start.astimezone() < subject.astimezone() < end.astimezone()


class EdXAttributes:
    """
    Our definitions of Product Type (Variant and Product) Attributes

    - if they start with variant_ they are on the variant level in the UI
    - if they start with product_type_ they are on the Product itself, but defines as unique per Product
      (all variants must supply this value and it must be 'SAME_FOR_ALL')
    """
    product_type_course_id = {
        'name': KeyGen.product_variant_attribute("parent_course_id"),
        'label': ls({'en': 'edX Course ID'}),
        'type': AttributeType(name='text'),
        'input_hint': TextInputHint.SINGLE_LINE
    }
    product_type_course_uuid = {
        'name': KeyGen.product_variant_attribute("parent_course_uuid"),
        'label': ls({'en': 'edX Course UUID'}),
        'type': AttributeType(name='text'),
        'input_hint': TextInputHint.SINGLE_LINE
    }
    variant_course_run_uuid = {
        'name': KeyGen.product_variant_attribute("uuid"),
        'label': ls({'en': 'edX Course Run UUID'}),
        'type': AttributeType(name='text'),
        'input_hint': TextInputHint.SINGLE_LINE
    }
    variant_course_run_id = {
        'name': KeyGen.product_variant_attribute("course_run_id"),
        'label': ls({'en': 'edX Course Run ID'}),
        'type': AttributeType(name='text'),
        'input_hint': TextInputHint.SINGLE_LINE
    }
    variant_search_text = {
        'name': KeyGen.product_variant_attribute("course_run_search_text"),
        'label': ls({'en': 'edX Course Search Text'}),
        'type': AttributeType(name='ltext'),
        'input_hint': TextInputHint.MULTI_LINE
    }


class Command(TimedCommand):
    help = "Import Discovery Courses to CommerceTools"

    course_product_type_key = KeyGen.product_type('course_verified')

    # Helpers
    def handle_commercetools_error(self, error: CommercetoolsError, exit_code: int = 127):
        """
        Standardize CommerceTools error while revealing "why" (for example, what API values were invalid.

        Args:
            error: CommercetoolsError Object
            exit_code: Shell Exit code (anything over 0 is a fatal error)
        """

        print(f"*** ERROR at ln{inspect.currentframe().f_back.f_lineno} => {error}")
        print(f"*** DETAILS => {error.errors}\n\n")

        self.print_reporting_time()

        if exit_code != 0:
            exit(exit_code)

    @staticmethod
    def fetch_from_discovery(index, last_sort, alter_query=None, **options):
        """
        Invoke Discovery's ES _search API and return it's result

        Args:
            index: Which ES index to use
            last_sort: The last pagination sort value from the final item in the last call
            alter_query: A mutator that can modify the query object before it is sent
                         (you can modify all parts of the query except pagination control)
            **options: Options (CLI input options) from the main method (`Command.handle`)

        Returns: urllib3.BaseHTTPResponse

        """
        query_template = """
        {
            "query": {"match_all": {}},
            "sort": [
                {"id": "asc"}
            ]
        }
        """

        query = json.loads(query_template)

        query['size'] = DISCO_MAX_PER_PAGE

        if alter_query:
            query = alter_query(query)

        if last_sort:
            last_sort_proper = [last_sort]

            if isinstance(last_sort, list):
                last_sort_proper = last_sort

            query['search_after'] = last_sort_proper

        if DISCO_DEBUG_ES:
            print(f"ES Query {index} => {json.dumps(query)}")

        return urllib3.request('GET', f"{options['discovery_host']}/{index}/_search",
                               headers={"Content-Type": "application/json"},
                               body=json.dumps(query))

    @staticmethod
    def es_result_pagination_return(es_result, result_key_name):
        # TODO: Calculate Pagination

        result = es_result.json()

        if DISCO_DEBUG_ES:
            print(f"ES Return => {result}")

        return {
            result_key_name: result['hits']['hits'],
            'done': True,
            'pagination_control_value': 1
        }

    @staticmethod
    def get_course_runs(parent_course_key, **options):
        def _mutator(es_query):
            """ Let's ensure were only getting the pertinent subset of course_runs for the subject """

            es_query['query'] = {'match': {'course_key': parent_course_key}}

            return es_query

        return Command.es_result_pagination_return(Command.fetch_from_discovery(
            DiscoIndex.COURSE_RUNS.value, None, alter_query=_mutator, **options
        ), 'runs')

    @staticmethod
    def get_courses(last_sort_index=None, **options):
        # TODO: Determine if done to support pagination, were using the search_after method (as its stable)
        #    https://www.elastic.co/guide/en/elasticsearch/reference/current/paginate-search-results.html#search-after

        return Command.es_result_pagination_return(Command.fetch_from_discovery(
            DiscoIndex.COURSES.value, last_sort_index, **options
        ), 'courses')

    @staticmethod
    def get_image_dimensions(url):
        """
        Get the Dimensions of an image based on URL

        Args:
            url: HTTP/S URL to Resource

        Returns (AssetDimensions): Dimensions of Image for CommerceTools

        """
        im = PILImage.open(BytesIO(urllib3.request('GET', url).data))
        return AssetDimensions(w=im.width, h=im.height)

    # Django Overrides
    def add_arguments(self, parser):
        parser.add_argument("discovery_host", nargs="?", type=str, default="http://127.0.0.1:9200")
        pass

    @no_translations
    def handle(self, *args, **options):
        container_key = KeyGen.import_container(f'discovery_{self.start.strftime("%Y_%m_%d")}')
        config = django.conf.settings.COMMERCETOOLS_CONFIG

        print(f'Using commercetools ImpEx config: {config["projectKey"]} / {config["importUrl"]}')

        import_client = Client(
            client_id=config["clientId"],
            client_secret=config["clientSecret"],
            scope=[config["scopes"]],
            url=config["importUrl"],
            token_url=config["authUrl"],
        ).with_project_key_value(config["projectKey"])

        try:
            import_client.import_containers().post(
                body=ImportContainerDraft(key=container_key,
                                          resource_type=ImportResourceType.PRODUCT_DRAFT)
            )
        except CommercetoolsError as _:
            pass

        container = import_client.import_containers().with_import_container_key_value(container_key).get()

        print(container)

        try:
            import_client.product_types().import_containers().with_import_container_key_value(container_key).post(
                ProductTypeImportRequest(resources=[
                    ProductTypeImport(
                        key=self.course_product_type_key,
                        name='edX Single Course',
                        description='A single edX LMS Course with Verification/Certification',
                        attributes=[
                            # Will appear at Product Level
                            AttributeDefinition(
                                type=EdXAttributes.product_type_course_id['type'],
                                name=EdXAttributes.product_type_course_id['name'],
                                label=EdXAttributes.product_type_course_id['label'],
                                is_searchable=True,
                                is_required=True,
                                attribute_constraint=AttributeConstraintEnum.SAME_FOR_ALL,
                                input_hint=EdXAttributes.product_type_course_id['input_hint']
                            ),
                            AttributeDefinition(
                                type=EdXAttributes.product_type_course_uuid['type'],
                                name=EdXAttributes.product_type_course_uuid['name'],
                                label=EdXAttributes.product_type_course_uuid['label'],
                                is_searchable=True,
                                is_required=True,
                                attribute_constraint=AttributeConstraintEnum.SAME_FOR_ALL,
                                input_hint=EdXAttributes.product_type_course_uuid['input_hint']
                            ),
                            # Will Appear at Variant Level
                            AttributeDefinition(
                                type=EdXAttributes.variant_course_run_id['type'],
                                name=EdXAttributes.variant_course_run_id['name'],
                                label=EdXAttributes.variant_course_run_id['label'],
                                is_searchable=True,
                                is_required=True,
                                attribute_constraint=AttributeConstraintEnum.UNIQUE,
                                input_hint=EdXAttributes.variant_course_run_id['input_hint']
                            ),
                            AttributeDefinition(
                                type=EdXAttributes.variant_course_run_uuid['type'],
                                name=EdXAttributes.variant_course_run_uuid['name'],
                                label=EdXAttributes.variant_course_run_uuid['label'],
                                is_searchable=True,
                                is_required=True,
                                attribute_constraint=AttributeConstraintEnum.UNIQUE,
                                input_hint=EdXAttributes.variant_course_run_uuid['input_hint']
                            ),
                            AttributeDefinition(
                                type=EdXAttributes.variant_search_text['type'],
                                name=EdXAttributes.variant_search_text['name'],
                                label=EdXAttributes.variant_search_text['label'],
                                is_searchable=True,
                                is_required=True,
                                attribute_constraint=AttributeConstraintEnum.UNIQUE,
                                input_hint=EdXAttributes.variant_search_text['input_hint']
                            )
                        ]
                    )
                ])
            )
        except CommercetoolsError as err:
            self.handle_commercetools_error(err, 1)

        course_key_ref = ProductTypeKeyReference(key=self.course_product_type_key)

        product_drafts = []

        for course in self.get_courses(**options)['courses']:
            course_data = course['_source']

            master_variant = None
            variants = []

            for crun in self.get_course_runs(course_data['key'], **options)['runs']:
                course_run_data = crun['_source']

                # Using the script start date will be more efficient
                script_start = self.start
                # some dates from ES aren't formatted EXACTLY as the datetime.date.fromisostring() call wants.
                crun_start = dateparser.parse(course_run_data['enrollment_start'])
                crun_end = dateparser.parse(course_run_data['paid_seat_enrollment_end'])

                images = []

                # noinspection PyBroadException
                try:
                    images.append(Image(
                        url=course_run_data['image_url'],
                        dimensions=self.get_image_dimensions(course_run_data['image_url']),
                        label="edX Course Tile Image"
                    ))
                except Exception as _:
                    pass

                variant_object = ProductVariantDraftImport(
                    key=KeyGen.product_variant(course_run_data['slug']),
                    sku=KeyGen.sku(course_run_data['first_enrollable_paid_seat_sku']),
                    images=images,
                    prices=[
                        PriceDraftImport(
                            value=TypedMoney(
                                type=MoneyType.CENT_PRECISION,
                                cent_amount=course_run_data['first_enrollable_paid_seat_price'] * 100,
                                currency_code='USD'
                            ),
                            valid_from=crun_start,
                            valid_until=crun_end,
                            key=KeyGen.product_variant_price(course_run_data['first_enrollable_paid_seat_sku'])
                        )
                    ],
                    attributes=[
                        TextAttribute(name=EdXAttributes.product_type_course_id['name'], value=course_data['key']),
                        TextAttribute(name=EdXAttributes.product_type_course_uuid['name'],
                                      value=course_data['uuid']),
                        TextAttribute(name=EdXAttributes.variant_course_run_id['name'],
                                      value=course_run_data['key']),
                        TextAttribute(
                            name=EdXAttributes.variant_course_run_uuid['name'],
                            value=course_run_data['uuid']
                        ),
                        LocalizableTextAttribute(
                            name=EdXAttributes.variant_search_text['name'],
                            value=ls({'en': course_run_data['text']})
                        ),
                    ]
                )

                if is_date_between(script_start, crun_start, crun_end):
                    master_variant = variant_object
                else:
                    variants.append(variant_object)

            # We need a master variant, so if we cant determine one, let's just pop one off
            if not master_variant:
                master_variant = variants.pop()

            product_drafts.append(ProductDraftImport(
                key=KeyGen.product(course_data['uuid']),
                product_type=course_key_ref,
                name=ls({"en": course_data['title']}),
                slug=ls({"en": KeyGen.product_slug(course_data['uuid'])}),
                publish=True,
                variants=variants,
                master_variant=master_variant,
            ))

        try:
            import_client.product_drafts().import_containers().with_import_container_key_value(container_key).post(
                ProductDraftImportRequest(resources=product_drafts)
            )
        except CommercetoolsError as err:
            self.handle_commercetools_error(err, 2)
