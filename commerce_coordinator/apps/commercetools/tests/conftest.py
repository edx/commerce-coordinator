""" Commercetools Client Testing Configuration and helper functions """

# pylint: disable=protected-access

import json
import os
import pathlib
import typing
from datetime import datetime

import requests_mock
from commercetools.platform.models import AuthenticationMode as CTAuthenticationMode
from commercetools.platform.models import Customer as CTCustomer
from commercetools.platform.models import CustomFields as CTCustomFields
from commercetools.platform.models import FieldContainer as CTFieldContainer
from commercetools.platform.models import Order as CTOrder
from commercetools.platform.models import TypeReference as CTTypeReference
from commercetools.platform.models import ProductProjectionPagedSearchResponse as CTProductProjectionPagedSearchResponse
from commercetools.testing import BackendRepository

from commerce_coordinator.apps.commercetools.catalog_info.constants import EdXFieldNames
from commerce_coordinator.apps.commercetools.clients import CommercetoolsAPIClient
from commerce_coordinator.apps.core.tests.utils import uuid4_str


class MonkeyPatch:
    """Monkeypath Utility Class"""
    STORE_KEY = 'MonkeyPatch'

    @staticmethod
    def is_monkey(obj):
        """Is the object monkey patched?"""
        return hasattr(obj, MonkeyPatch.STORE_KEY)

    @staticmethod
    def monkey(obj, methods: dict):
        """Monkey patch and object"""
        old_attrs = {}
        for key in methods.keys():
            old_attrs[key] = getattr(obj, key)
            setattr(obj, key, methods[key])
        setattr(obj, MonkeyPatch.STORE_KEY, old_attrs)
        return obj

    @staticmethod
    def unmonkey(obj):
        """Remove monkey patches"""
        old_attrs = getattr(obj, MonkeyPatch.STORE_KEY)

        for key in old_attrs.keys():
            setattr(obj, key, old_attrs[key])

        delattr(obj, MonkeyPatch.STORE_KEY)
        return obj


StorageKey = typing.Literal[  # So people don't have to guess the storage keys
    'cart', 'category', 'channel', 'cart-discounts', 'custom-object', 'customer-group',
    'customer', 'discount-code', 'extension', 'inventory-entry', 'order', 'payment',
    'project', 'product', 'product-discount', 'product-type', 'review', 'shipping-method',
    'shopping-list', 'state', 'store', 'tax-category', 'type', 'subscription', 'zones'
]


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
                 repo: BackendRepository):
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
        self.client = CommercetoolsAPIClient()

    def __del__(self):
        """ Deconstructor """
        self._mocker.stop()

    # We have to hack the SDK a small bit to make some things work, these are helpers to keep this uniform
    def fetch_from_storage(self, singular_item_name: StorageKey, klass: type = None):
        """
        Fetch a set of objects from internal backing store storage, these are in raw form and need to be deserialized

        Args:
            singular_item_name: Storage Key
            klass (type): (As Class Name, not __class__) if supplied, we will give you instances of an object and not
                just dictionaries
        """
        # noinspection PyProtectedMember
        raw_objs = list(self.backend_repo._storage._stores[singular_item_name].values())

        if klass:
            # noinspection PyUnresolvedReferences
            return [klass.deserialize(o) for o in raw_objs]

        return raw_objs

    def get_base_url_from_client(self) -> str:
        # noinspection PyProtectedMember
        return self.client.base_client._base_url

    # Instance Creators
    @staticmethod
    def new_instance():
        """
        Create a new instance of the API Set with full lifecycle management
        """
        mocker = requests_mock.Mocker(real_http=True, case_sensitive=False)
        repo = BackendRepository()
        repo.register(mocker)
        return APITestingSet(mocker, repo)


# Data Blobs
DEFAULT_ORDER_VARIANT_SKU = "course-v1:edX+DemoX+Demo_Course"

def gen_order(uuid_id) -> CTOrder:
    with open(os.path.join(pathlib.Path(__file__).parent.resolve(), 'raw_ct_order.json')) as f:
        obj = json.load(f)
        obj['id'] = uuid_id
        return CTOrder.deserialize(obj)


def gen_variant_search_result() -> CTProductProjectionPagedSearchResponse:
    with open(os.path.join(pathlib.Path(__file__).parent.resolve(), 'raw_variant_search.json')) as f:
        obj = json.load(f)
        return CTProductProjectionPagedSearchResponse.deserialize(obj)


def gen_order_history(num=1) -> typing.List[CTOrder]:
    return [gen_order(uuid4_str()) for _ in range(num)]


def gen_example_customer() -> CTCustomer:
    return CTCustomer.deserialize(json.loads(
        """
        {
          "id": "f7f54eef-3ece-4bd2-a432-ffc3b3398507",
          "version": 17,
          "createdAt": "2023-09-25T16:21:19.698000+00:00",
          "lastModifiedAt": "2023-10-05T17:48:27.495000+00:00",
          "customerNumber": "raisinets",
          "lastModifiedBy": {
            "clientId": "wdnYt1yvChl2Fug2V_7-Dyf_"
          },
          "createdBy": {
            "clientId": "zUJB9Qh3BIc7wMABr38piyuN"
          },
          "email": "test35@example.com",
          "password": "****gCk=",
          "firstName": "Glenns",
          "lastName": "User",
          "middleName": "Testing",
          "title": "",
          "addresses": [
            {
              "id": "G6cbqTeY",
              "country": "US",
              "postalCode": "54000",
              "city": "New Jersey"
            }
          ],
          "defaultShippingAddressId": "G6cbqTeY",
          "shippingAddressIds": [
            "G6cbqTeY"
          ],
          "billingAddressIds": [
          ],
          "isEmailVerified": false,
          "custom": {
            "type": {
              "typeId": "type",
              "id": "52dc06db-07be-458e-80db-253c5d6c7e59"
            },
            "fields": {
              "edx-lms_user_id": "17",
              "edx-lms_user_name": "some_un"
            }
          },
          "salutation": "",
          "stores": [
          ],
          "authenticationMode": "Password"
        }
        """
    ))


DEFAULT_EDX_LMS_USER_ID = 127


def gen_customer(email: str, un: str):
    return CTCustomer(
        email=email,
        custom=CTCustomFields(
            type=CTTypeReference(
                id=uuid4_str()
            ),
            fields=CTFieldContainer({
                EdXFieldNames.LMS_USER_NAME: un,
                EdXFieldNames.LMS_USER_ID: DEFAULT_EDX_LMS_USER_ID
            })
        ),
        version=3,
        addresses=[],
        authentication_mode=CTAuthenticationMode.PASSWORD,
        created_at=datetime.now(),
        id=uuid4_str(),
        is_email_verified=True,
        last_modified_at=datetime.now()
    )
