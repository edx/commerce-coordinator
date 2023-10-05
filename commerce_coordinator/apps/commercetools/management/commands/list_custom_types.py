import json

from django.core.management.base import no_translations

from commerce_coordinator.apps.commercetools.management.commands._ct_api_client_command import (
    CommercetoolsAPIClientCommand
)

MAX_RESULTS = 200


class Command(CommercetoolsAPIClientCommand):
    help = "List the custom types defined in Commercetools (as this isn't available via the Merchant Center)"

    # Django Overrides
    def add_arguments(self, parser):
        parser.add_argument("--offset", nargs='?', type=int, default=0)

    @no_translations
    def handle(self, *args, **options):
        offset = options['offset']
        ret = self.ct_api_client.base_client.types.query(limit=MAX_RESULTS + 1, offset=offset)

        types = ret.results

        if len(types) > MAX_RESULTS:
            types.pop()  # +1 not needed

        print(json.dumps(
            [x.serialize() for x in types],
            indent=2
        ))

        if ret.count <= MAX_RESULTS:
            print("No More Results Available")
        else:
            print(f"There are more results, paginating at {MAX_RESULTS}, current offset: {offset}")
