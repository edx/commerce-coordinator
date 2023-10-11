import typing

import requests_mock
from commercetools import Client
from commercetools.testing import BackendRepository

from commerce_coordinator.apps.commercetools.clients import CommercetoolsAPIClient

TESTING_COMMERCETOOLS_CONFIG = {
    # These values have special meaning to the CT SDK Unit Testing, and will fail if changed.
    'clientId': "client-id",
    'clientSecret': "client-secret",
    'scopes': "manage_project:todo",
    'apiUrl': "https://api.europe-west1.gcp.commercetools.com",
    'authUrl': "https://auth.europe-west1.gcp.commercetools.com/oauth/token",
    'projectKey': "unittest",
}


def _default_client_factory() -> CommercetoolsAPIClient:
    """Create a default API Client using the CT Test Config Settings"""
    cfg = TESTING_COMMERCETOOLS_CONFIG
    return CommercetoolsAPIClient(Client(
        project_key=cfg['projectKey'],
        client_id=cfg['clientId'],
        client_secret=cfg['clientSecret'],
        scope=[],
        url=cfg['apiUrl'],
        token_url=cfg['authUrl'],
    ))


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

    def __init__(self,
                 mocker: requests_mock.Mocker,
                 repo: BackendRepository,
                 client_builder: typing.Callable[[], CommercetoolsAPIClient] = _default_client_factory):
        """
        Create a new instance, please use APITestingSet.new_instance() instead.

        Args:
            mocker (requests_mock.Mocker): Instance of an API Requests mock, that has been bound to the Backend Repo
            repo (BackendRepository): Backend Data Tracker, bound to a Mocker
        """

        self._mocker = mocker
        self.backend_repo = repo
        mocker.start()  # Creating a client calls oauth, so Mocker needs to be live first.
        # this is to test some code used in production but only needs to make oauth callbacks
        self.client = client_builder()

    def __del__(self):
        """ Deconstructor """
        self._mocker.stop()

    @staticmethod
    def new_instance(
            client_builder: typing.Optional[typing.Callable[[], CommercetoolsAPIClient]] = _default_client_factory):
        """
        Create a new instance of the API Set with full lifecycle management

        Args:
            client_builder (()->CommercetoolsAPIClient): Permits you to delegate Client building to outside scope
        """
        mocker = requests_mock.Mocker(real_http=True, case_sensitive=False)
        repo = BackendRepository()
        repo.register(mocker)
        return APITestingSet(mocker, repo, client_builder)
