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
from commercetools.platform.models import LineItemReturnItem as CTLineItemReturnItem
from commercetools.platform.models import MoneyType as CTMoneyType
from commercetools.platform.models import Order as CTOrder
from commercetools.platform.models import Payment as CTPayment
from commercetools.platform.models import PaymentState
from commercetools.platform.models import Product as CTProduct
from commercetools.platform.models import ProductProjectionPagedSearchResponse as CTProductProjectionPagedSearchResponse
from commercetools.platform.models import ReturnPaymentState, ReturnShipmentState
from commercetools.platform.models import Transaction as CTTransaction
from commercetools.platform.models import TransactionState, TransactionType
from commercetools.platform.models import TypedMoney as CTTypedMoney
from commercetools.platform.models import TypeReference as CTTypeReference
from commercetools.platform.models.state import State as CTLineItemState
from commercetools.platform.models.state import StateTypeEnum as CTStateType
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
        mocker = requests_mock.Mocker(real_http=True, case_sensitive=True)
        repo = BackendRepository()
        repo.register(mocker)
        return APITestingSet(mocker, repo)


# Data Blobs
def gen_order(uuid_id, with_discount=True) -> CTOrder:
    """
    Generate a CTOrder object from a json file
    """
    order_json_file = ('raw_ct_order.json' if with_discount
                       else 'raw_ct_order_without_discount.json')
    with open(os.path.join(pathlib.Path(__file__).parent.resolve(), order_json_file)) as f:
        obj = json.load(f)
        obj['id'] = uuid_id
        return CTOrder.deserialize(obj)


def gen_payment():
    return CTPayment(
        id=uuid4_str(),
        version=1,
        created_at=datetime.now(),
        last_modified_at=datetime.now(),
        key="pi_4MtwBwLkdIwGlenn28a3tqPa",
        amount_planned=4900,
        payment_method_info={},
        payment_status=PaymentState.PAID,
        transactions=[gen_transaction(TransactionType.REFUND, CTTypedMoney(
            currency_code='USD',
            cent_amount=1000,
            type=CTMoneyType.CENT_PRECISION,
            fraction_digits=2,
        ))],
        interface_interactions=[]
    )


def gen_payment_with_multiple_transactions(*args):
    """
    Generate a CTPayment object with multiple transaction records
    """
    transactions = []
    for i in range(0, len(args), 2):
        transaction = gen_transaction(args[i], args[i+1])
        transactions.append(transaction)

    return CTPayment(
        id=uuid4_str(),
        version=1,
        created_at=datetime.now(),
        last_modified_at=datetime.now(),
        amount_planned=4900,
        payment_method_info={},
        payment_status=PaymentState.PAID,
        transactions=transactions,
        interface_interactions=[]
    )


def gen_transaction(transaction_type=None, amount=None) -> CTTransaction:
    return CTTransaction(
        id=uuid4_str(),
        type=transaction_type,
        amount=amount,
        timestamp=datetime.now(),
        state=TransactionState.SUCCESS,
        interaction_id='ch_3P9RWsH4caH7G0X11toRGUJf'
    )


def gen_product() -> CTProduct:
    with open(os.path.join(pathlib.Path(__file__).parent.resolve(), 'raw_ct_product.json')) as f:
        obj = json.load(f)
        return CTProduct.deserialize(obj)


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
        first_name='John',
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


def gen_retired_customer(first_name: str, last_name: str, email: str, un: str):
    return CTCustomer(
        email=email,
        first_name=first_name,
        last_name=last_name,
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


def gen_return_item(order_line_id: str, payment_state: ReturnPaymentState) -> CTLineItemReturnItem:
    return CTLineItemReturnItem(
        id=uuid4_str(),
        quantity=1,
        shipment_state=ReturnShipmentState.RETURNED,
        payment_state=payment_state,
        last_modified_at=datetime.now(),
        created_at=datetime.now(),
        line_item_id=order_line_id
    )


def gen_line_item_state() -> CTLineItemState:
    return CTLineItemState(
        id=uuid4_str(),
        version=2,
        created_at=datetime.now(),
        last_modified_at=datetime.now(),
        key='2u-fulfillment-pending-state',
        type=CTStateType.LINE_ITEM_STATE,
        initial=False,
        built_in=False,
    )
