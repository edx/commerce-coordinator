import json
import typing
from datetime import datetime

import django.conf
from commercetools.base_client import BaseClient
from commercetools.utils import BaseTokenSaver
# noinspection PyProtectedMember
from django.core.management.base import BaseCommand, no_translations
from requests.adapters import HTTPAdapter

JSON_INDENTATION = 2


class ArbitraryApiClient(BaseClient):
    """ This allows us to ping any URL not provided by the SDK with Authentication """

    def __init__(self, project_key: str = None, client_id: str = None, client_secret: str = None,
                 scope: typing.List[str] = None, url: str = None, token_url: str = None,
                 token_saver: BaseTokenSaver = None, http_adapter: HTTPAdapter = None) -> None:
        super().__init__(project_key, client_id, client_secret, scope, url, token_url, token_saver, http_adapter)

    def get(self, endpoint: str, params=None, headers: typing.Dict[str, str] = None,
            options: typing.Dict[str, typing.Any] = None) -> typing.Any:
        if params is None:
            params = dict()
        return super()._get(endpoint, params, headers, options)


class Command(BaseCommand):
    help = "Check import container status in CommerceTools"

    start = datetime.now()

    # Helpers
    def print_reporting_time(self):
        delta = datetime.now() - self.start

        print(f"Started at: {self.start.strftime('%Y-%m-%d, %H:%M:%S')}, took {str(delta)}\n")

    # Django Overrides
    def add_arguments(self, parser):
        parser.add_argument("container_name", nargs='?', type=str,
                            default=f'edx-container-discovery_{self.start.strftime("%Y_%m_%d")}')
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

        container_key_name = options['container_name']

        # This API isn't available in the SDK, but we can Hijack the SDK to make it so :D
        result = import_client.get(f'/{config["projectKey"]}/import-containers/{container_key_name}/import-operations')

        if result.raw.status != 200:
            print(f"Error communicating with server, status code: {result.raw.status}")
            exit(1)

        print(json.dumps(json.loads(result.content), indent=JSON_INDENTATION))

        self.print_reporting_time()
