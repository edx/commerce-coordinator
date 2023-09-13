import pprint

import django.conf
from commercetools.importapi import Client
from django.core.management.base import no_translations

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

        import_client = Client(
            client_id=config["clientId"],
            client_secret=config["clientSecret"],
            scope=[config["scopes"]],
            url=config["importUrl"],
            token_url=config["authUrl"],
        ).with_project_key_value(project_key=config["projectKey"])

        container_key_name = options['container_name'][0]

        result = import_client.import_containers().with_import_container_key_value(container_key_name).delete()

        pprint.pp(result.serialize(), depth=500, indent=1)

        self.print_reporting_time()
