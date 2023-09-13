import json

import django.conf
from django.core.management.base import no_translations

from commerce_coordinator.apps.commercetools.management.commands._arbitrary_api_client import ArbitraryApiClient
from commerce_coordinator.apps.commercetools.management.commands._timed_command import TimedCommand

JSON_INDENTATION = 2


class Command(TimedCommand):
    help = "Delete an impot container in CommerceTools"

    # Django Overrides
    def add_arguments(self, parser):
        parser.add_argument("container_name", nargs=1, type=str)
        pass

    @no_translations
    def handle(self, *args, **options):
        config = django.conf.settings.COMMERCETOOLS_CONFIG

        print(f'Using commercetools ImpEx config: {config["projectKey"]} / {config["importUrl"]}')

        import_client = ArbitraryApiClient(
            project_key=config["projectKey"],
            client_id=config["clientId"],
            client_secret=config["clientSecret"],
            scope=[config["scopes"]],
            url=config["importUrl"],
            token_url=config["authUrl"],
        )

        container_key_name = options['container_name'][0]

        # This API isn't available in the SDK, but we can Hijack the SDK to make it so :D
        result = import_client.delete(f'/{config["projectKey"]}/import-containers/{container_key_name}')

        if result.raw.status != 200:
            print(f"Error communicating with server, status code: {result.raw.status}")
            exit(1)

        print(json.dumps(json.loads(result.content), indent=JSON_INDENTATION))

        self.print_reporting_time()
