import typing

import pytest
import requests_mock
from commercetools import Client
from commercetools.testing import BackendRepository

from commerce_coordinator.apps.commercetools.clients import CommercetoolsAPIClient


def commercetools_client_tuple(
) -> typing.Tuple[requests_mock.Mocker, BackendRepository, CommercetoolsAPIClient]:
    requests_mock.mock.case_sensitive = False
    with requests_mock.Mocker(real_http=False, case_sensitive=False) as m:
        repo = BackendRepository()
        repo.register(m)
        return m, repo, CommercetoolsAPIClient(Client(
            project_key="unittest",
            client_id="client-id",
            client_secret="client-secret",
            scope=[],
            url="https://api.europe-west1.gcp.commercetools.com",
            token_url="https://auth.europe-west1.gcp.commercetools.com/oauth/token",
        ))


# @pytest.fixture(scope="function")
# def commercetools_client_tuple(
# ) -> typing.Generator[typing.Tuple[requests_mock.Mocker, BackendRepository, CommercetoolsAPIClient], None, None]:
#     requests_mock.mock.case_sensitive = False
#     with requests_mock.Mocker(real_http=False, case_sensitive=False) as m:
#         repo = BackendRepository()
#         repo.register(m)
#         yield m, repo, CommercetoolsAPIClient(Client(
#             project_key="unittest",
#             client_id="client-id",
#             client_secret="client-secret",
#             scope=[],
#             url="https://api.europe-west1.gcp.commercetools.com",
#             token_url="https://auth.europe-west1.gcp.commercetools.com/oauth/token",
#         ))
#         repo.internal = None
