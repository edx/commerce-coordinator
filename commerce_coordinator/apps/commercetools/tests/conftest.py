import requests_mock
from commercetools import Client
from commercetools.testing import BackendRepository

from commerce_coordinator.apps.commercetools.clients import CommercetoolsAPIClient


class APITestingSet:
    """
    Coordinator API Testing Set

    Create a sed of testing classes including a storage repo and a client while also managing the Request Mockers
    lifespan

    A lot of this code uses examples found within commercetools.testing, however it has some lifecycle issues if
    you're not using fixtures and functional testing in pytest. Since were using unittest.TestCase, we had to mod it
    a bit to meet our needs.
    """

    _mocker: requests_mock.Mocker
    """ *PRIVATE* instance of the request Mocker, we need to control its life cycle, thus its private"""

    backend_repo: BackendRepository
    """ Storage Repository, incase youd like to example it"""
    client: CommercetoolsAPIClient
    """ Coordinatior API Client for Commerce Tools """

    def __init__(self, mocker: requests_mock.Mocker, repo: BackendRepository):
        """
        Create a new instance, please use APITestingSet.new_instance() instead.

        Args:
            mocker (requests_mock.Mocker): Instance of an API Requests mock, that has been bound to the Backend Repo
            repo (BackendRepository): Backend Data Tracker, bound to a Mocker
        """

        self._mocker = mocker
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
        """ Deconstructor """
        self._mocker.stop()

    @staticmethod
    def new_instance():
        """ Create a new instance of the API Set with full lifecycle management """
        mocker = requests_mock.Mocker(real_http=True, case_sensitive=False)
        repo = BackendRepository()
        repo.register(mocker)
        return APITestingSet(mocker, repo)
