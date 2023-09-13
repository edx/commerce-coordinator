import typing

from commercetools.base_client import BaseClient
from commercetools.utils import BaseTokenSaver
from requests.adapters import HTTPAdapter


class ArbitraryApiClient(BaseClient):
    """ This allows us to ping any URL not provided by the SDK with Authentication """

    def __init__(self, project_key: str = None, client_id: str = None, client_secret: str = None,
                 scope: typing.List[str] = None, url: str = None, token_url: str = None,
                 token_saver: BaseTokenSaver = None, http_adapter: HTTPAdapter = None) -> None:
        super().__init__(project_key, client_id, client_secret, scope, url, token_url, token_saver, http_adapter)

    def delete(self, endpoint: str, params=None, headers: typing.Dict[str, str] = None,
               options: typing.Dict[str, typing.Any] = None) -> typing.Any:
        if params is None:
            params = {}
        return super()._delete(endpoint, params, headers, options)

    def get(self, endpoint: str, params=None, headers: typing.Dict[str, str] = None,
            options: typing.Dict[str, typing.Any] = None) -> typing.Any:
        if params is None:
            params = dict()
        return super()._get(endpoint, params, headers, options)
