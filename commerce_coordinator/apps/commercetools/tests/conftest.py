import requests_mock
from commercetools import Client
from commercetools.testing import BackendRepository

from commerce_coordinator.apps.commercetools.clients import CommercetoolsAPIClient


class APITestingSet:
    mocker: requests_mock.Mocker
    backend_repo: BackendRepository
    client: CommercetoolsAPIClient

    def __init__(self, mocker: requests_mock.Mocker, repo: BackendRepository):
        self.mocker = mocker
        self.backend_repo = repo
        mocker.start()  # Creating a client calls oauth, so Mocker needs to be live first.
        self.client = CommercetoolsAPIClient(Client(
            project_key="unittest",
            client_id="client-id",
            client_secret="client-secret",
            scope=[],
            url="https://api.europe-west1.gcp.commercetools.com",
            token_url="https://auth.europe-west1.gcp.commercetools.com/oauth/token",
        ))

    def __del__(self):
        self.mocker.stop()

    @staticmethod
    def new_instance():
        m = requests_mock.Mocker(real_http=True, case_sensitive=False)
        repo = BackendRepository()
        repo.register(m)
        return APITestingSet(m, repo)
