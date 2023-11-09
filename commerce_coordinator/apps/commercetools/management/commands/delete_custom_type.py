import json

from django.core.management.base import no_translations

from commerce_coordinator.apps.commercetools.management.commands._ct_api_client_command import (
    CommercetoolsAPIClientCommand
)


class Command(CommercetoolsAPIClientCommand):
    help = "Delete a custom type in Commercetools, this will fail if even a single object is assigned this type."

    # Django Overrides
    def add_arguments(self, parser):
        parser.add_argument("type_key", nargs='?', type=str)

    @no_translations
    def handle(self, *args, **options):
        type_key = options['type_key']
        ret = self.ct_api_client.base_client.types.get_by_key(type_key)
        self.ct_api_client.base_client.types.delete_by_key(type_key, version=ret.version)
        print(json.dumps(ret.serialize()))
