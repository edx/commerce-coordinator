import inspect
import json
from io import BytesIO

import django.conf
import urllib3
from commercetools import CommercetoolsError
from commercetools.importapi import Client
from commercetools.importapi.models import AssetDimensions, AttributeConstraintEnum, \
    AttributeDefinition, AttributeType, Image, LocalizedString, \
    MoneyType, PriceDraftImport, ProductDraftImport, ProductTypeImport, \
    ProductTypeKeyReference, ProductVariantDraftImport, TextAttribute, TypedMoney
# noinspection PyProtectedMember
from commercetools.importapi.models.importcontainers import ImportContainerDraft, ImportResourceType
from commercetools.importapi.models.importrequests import ProductDraftImportRequest, ProductTypeImportRequest
from django.core.management.base import BaseCommand, no_translations
from PIL import Image as PILImage

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
# TODO: Get rid of Magic Strings

# ##  ssh grmartin@theseus.sandbox.edx.org -L 9200:127.0.0.1:9200

DISCO_MAX_PER_PAGE = 10


def ls(string_dict) -> LocalizedString:  # forced return typehint/coercion intentional to avoid bad IDE warnings
    """ Make a LocalizedString that doesn't freak out type checking, assign en to en-US as well. """
    if 'en' in string_dict:
        # Keys are CASE sensitive. String matching the pattern ^[a-z]{2}(-[A-Z]{2})?$ representing an IETF language tag
        string_dict['en-US'] = string_dict['en']

    return string_dict


class Command(BaseCommand):
    help = "Import Discovery Courses to CommerceTools"
    course_product_type_key = 'edx-course_verified'

    # Helpers
    @staticmethod
    def handle_commercetools_error(error: CommercetoolsError, exit_code: int):
        """
        Standardize CommerceTools error while revealing "why" (for example what API values were invalid.

        Args:
            error: CommercetoolsError Object
            exit_code: Shell Exit code (anything over 0 is a fatal error)
        """

        print(f"*** ERROR at ln{inspect.currentframe().f_back.f_lineno} => {error}")
        print(f"*** DETAILS => {error.errors}\n\n")

        if exit_code > 0:
            exit(exit_code)

    @staticmethod
    def fetch_from_discovery(index, last_sort, alter_query=None, **options):
        """
        Invoke Discoery's ES _search API and return it's result

        Args:
            index: Which ES index to use
            last_sort: The last pagination sort value from the final item in the last call
            alter_query: A mutator that can modify the query object before it is sent
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
            query['search_after'] = [last_sort]

        print(f"ES Query {index} => {json.dumps(query)}")

        return urllib3.request('GET', f"{options['discovery_host']}/{index}/_search",
                               headers={"Content-Type": "application/json"},
                               body=json.dumps(query))

    @staticmethod
    def get_course_runs(parent_course_key, **options):
        def _mutator(es_query):
            es_query['query'] = {'match': {'course_key': parent_course_key}}
            return es_query

        return {
            'runs': Command.fetch_from_discovery(
                'course_run', None, alter_query=_mutator, **options
            ).json()['hits']['hits'],
            'done': True,
            'page': 1
        }

    @staticmethod
    def get_courses(last_sort_index=None, **options):
        # TODO: Determine if done to support pagnation, were using the search_after method (as its stable)
        #    https://www.elastic.co/guide/en/elasticsearch/reference/current/paginate-search-results.html#search-after

        return {
            'courses': Command.fetch_from_discovery('course', last_sort_index, **options).json()['hits']['hits'],
            'done': True,
            'page': 1
        }

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
        container_key = "glenns_container"
        config = django.conf.settings.COMMERCETOOLS_CONFIG

        print(f'Using commercetools config: {config["projectKey"]} / {config["apiUrl"]}')

        import_client = Client(
            # project_key=config["projectKey"],
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
                            # Will Appear at Variant Level
                            AttributeDefinition(
                                type=AttributeType(name='text'),
                                name="edx-uuid",
                                label=ls({'en': 'edX UUID'}),
                                is_searchable=True,
                                is_required=True
                            ),
                            AttributeDefinition(
                                type=AttributeType(name='text'),
                                name="edx-course_run_id",
                                label=ls({'en': 'edX Course Run ID'}),
                                is_searchable=True,
                                is_required=True,
                                attribute_constraint=AttributeConstraintEnum.UNIQUE
                            ),
                            # Will appear at Product Level
                            AttributeDefinition(
                                type=AttributeType(name='text'),
                                name="edx-parent_course_id",
                                label=ls({'en': 'edX Parent Course ID'}),
                                is_searchable=True,
                                is_required=True,
                                attribute_constraint=AttributeConstraintEnum.SAME_FOR_ALL
                            ),
                            AttributeDefinition(
                                type=AttributeType(name='text'),
                                name="edx-parent_course_uuid",
                                label=ls({'en': 'edX Parent Course UUID'}),
                                is_searchable=True,
                                is_required=True,
                                attribute_constraint=AttributeConstraintEnum.SAME_FOR_ALL
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

            variants = []
            for crun in self.get_course_runs(course_data['key'], **options)['runs']:
                course_run_data = crun['_source']
                variants.append(ProductVariantDraftImport(
                    key=f"edx-{course_run_data['slug']}",
                    sku=f"edx-sku-{course_run_data['first_enrollable_paid_seat_sku']}",
                    images=[
                        Image(
                            url=course_run_data['image_url'],
                            dimensions=self.get_image_dimensions(course_run_data['image_url'])
                        )
                    ],
                    prices=[
                        PriceDraftImport(
                            value=TypedMoney(
                                type=MoneyType.CENT_PRECISION,
                                cent_amount=course_run_data['first_enrollable_paid_seat_price'] * 100,
                                currency_code='USD'
                            ),
                            key=f"edx-usd_price-{course_run_data['first_enrollable_paid_seat_sku']}"
                        )
                    ],
                    attributes=[
                        TextAttribute(name="edx-uuid", value=course_run_data['uuid']),
                        TextAttribute(name="edx-parent_course_id", value=course_data['key']),
                        TextAttribute(name="edx-parent_course_uuid", value=course_data['uuid']),
                        TextAttribute(name="edx-course_run_id", value=course_run_data['key']),
                    ]
                ))

            product_drafts.append(ProductDraftImport(
                key=f"edx-{course_data['uuid']}",
                product_type=course_key_ref,
                name=ls({"en": course_data['title']}),
                slug=ls({"en": f"edx-{course_data['uuid']}"}),
                publish=True,
                variants=variants,
            ))

        try:
            import_client.product_drafts().import_containers().with_import_container_key_value(container_key).post(
                ProductDraftImportRequest(resources=product_drafts)
            )
        except CommercetoolsError as err:
            self.handle_commercetools_error(err, 2)
