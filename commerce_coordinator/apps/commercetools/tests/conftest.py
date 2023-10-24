import json
import typing
import uuid

import requests_mock
from commercetools import Client
from commercetools.platform.models import Customer as CTCustomer
from commercetools.platform.models import Order as CTOrder
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
    def new_instance(
        client_builder: typing.Optional[typing.Callable[[], CommercetoolsAPIClient]] = _default_client_factory
    ):
        """
        Create a new instance of the API Set with full lifecycle management

        Args:
            client_builder (()->CommercetoolsAPIClient): Permits you to delegate Client building to outside scope
        """
        mocker = requests_mock.Mocker(real_http=True, case_sensitive=False)
        repo = BackendRepository()
        repo.register(mocker)
        return APITestingSet(mocker, repo, client_builder)


# Data Blobs
def gen_order(uuid_id):
    obj = json.loads(
        """
          {
            "version": 6,
            "createdAt": "2023-09-25T16:21:21.504000+00:00",
            "lastModifiedAt": "2023-09-25T16:22:04.707000+00:00",
            "lastModifiedBy": {
              "clientId": "zUJB9Qh3BIc7wMABr38piyuN"
            },
            "createdBy": {
              "clientId": "zUJB9Qh3BIc7wMABr38piyuN"
            },
            "customerId": "f7f54eef-3ece-4bd2-a432-ffc3b3398507",
            "customerEmail": "test35@example.com",
            "lineItems": [
              {
                "id": "19e42341-4214-4d22-863b-de719f2ca614",
                "productId": "51b6a60d-83a8-47c0-9a34-ef7c6a949f82",
                "productKey": "edx-prod-142765f0-7c1e-4ac4-93fe-8516d87f985e",
                "name": {
                  "en": "Demonstration Course",
                  "en-US": "Demonstration Course"
                },
                "productSlug": {
                  "en": "edx-142765f0-7c1e-4ac4-93fe-8516d87f985e",
                  "en-US": "edx-142765f0-7c1e-4ac4-93fe-8516d87f985e"
                },
                "productType": {
                  "typeId": "product-type",
                  "id": "e70246dd-dd21-4e4a-b4a4-fbb39e3ec528"
                },
                "variant": {
                  "id": 1,
                  "sku": "edx-sku-8CF08E5",
                  "key": "edx-var-demonstration-course-course-v1-edx-demox-demo-course",
                  "prices": [
                    {
                      "id": "c4d32806-adbd-482f-b5d2-03b2016e2c95",
                      "key": "edx-usd_price-8CF08E5",
                      "value": {
                        "centAmount": 14900,
                        "currencyCode": "USD",
                        "type": "centPrecision",
                        "fractionDigits": 2
                      },
                      "validFrom": "2013-02-05T00:00:00+00:00",
                      "validUntil": "2024-03-19T17:52:43.355000+00:00"
                    }
                  ],
                  "attributes": [
                    {
                      "name": "edx-parent_course_id",
                      "value": "edX+DemoX"
                    },
                    {
                      "name": "edx-parent_course_uuid",
                      "value": "142765f0-7c1e-4ac4-93fe-8516d87f985e"
                    },
                    {
                      "name": "edx-course_run_id",
                      "value": "course-v1:edX+DemoX+Demo_Course"
                    },
                    {
                      "name": "edx-uuid",
                      "value": "05cfefe9-8eae-41e0-8e44-52a2144668af"
                    },
                    {
                      "name": "2u-fulfillment_system",
                      "value": "LMS"
                    },
                    {
                      "name": "2u-lob",
                      "value": "edX"
                    }
                  ],
                  "images": [
                    {
                      "url": "https://theseus.sandbox.edx.org/asset-v1:edX+DemoX+Demo_Course+type@asset+block@images_course_image.jpg",
                      "dimensions": {
                        "w": 375,
                        "h": 200
                      },
                      "label": "edX Course Tile Image"
                    }
                  ],
                  "assets": [
                  ]
                },
                "price": {
                  "id": "c4d32806-adbd-482f-b5d2-03b2016e2c95",
                  "key": "edx-usd_price-8CF08E5",
                  "value": {
                    "centAmount": 14900,
                    "currencyCode": "USD",
                    "type": "centPrecision",
                    "fractionDigits": 2
                  },
                  "validFrom": "2013-02-05T00:00:00+00:00",
                  "validUntil": "2024-03-19T17:52:43.355000+00:00"
                },
                "quantity": 1,
                "totalPrice": {
                  "centAmount": 14900,
                  "currencyCode": "USD",
                  "type": "centPrecision",
                  "fractionDigits": 2
                },
                "discountedPricePerQuantity": [
                ],
                "taxedPrice": {
                  "totalNet": {
                    "centAmount": 13545,
                    "currencyCode": "USD",
                    "type": "centPrecision",
                    "fractionDigits": 2
                  },
                  "totalGross": {
                    "centAmount": 14900,
                    "currencyCode": "USD",
                    "type": "centPrecision",
                    "fractionDigits": 2
                  },
                  "totalTax": {
                    "centAmount": 1355,
                    "currencyCode": "USD",
                    "type": "centPrecision",
                    "fractionDigits": 2
                  }
                },
                "taxedPricePortions": [
                ],
                "state": [
                  {
                    "quantity": 1,
                    "state": {
                      "typeId": "state",
                      "id": "6d82d691-af5a-4ece-a9a5-1e36aebbf684"
                    }
                  }
                ],
                "taxRate": {
                  "id": "Yke-TKWo",
                  "name": "GST",
                  "amount": 0.1,
                  "includedInPrice": true,
                  "country": "US",
                  "subRates": [
                  ]
                },
                "perMethodTaxRate": [
                ],
                "priceMode": "Platform",
                "lineItemMode": "Standard",
                "addedAt": "2023-09-25T16:21:20.672000+00:00",
                "lastModifiedAt": "2023-09-25T16:21:20.672000+00:00"
              }
            ],
            "customLineItems": [
            ],
            "totalPrice": {
              "centAmount": 14900,
              "currencyCode": "USD",
              "type": "centPrecision",
              "fractionDigits": 2
            },
            "taxedPrice": {
              "totalNet": {
                "centAmount": 13545,
                "currencyCode": "USD",
                "type": "centPrecision",
                "fractionDigits": 2
              },
              "totalGross": {
                "centAmount": 14900,
                "currencyCode": "USD",
                "type": "centPrecision",
                "fractionDigits": 2
              },
              "taxPortions": [
                {
                  "name": "GST",
                  "rate": 0.1,
                  "amount": {
                    "centAmount": 1355,
                    "currencyCode": "USD",
                    "type": "centPrecision",
                    "fractionDigits": 2
                  }
                }
              ],
              "totalTax": {
                "centAmount": 1355,
                "currencyCode": "USD",
                "type": "centPrecision",
                "fractionDigits": 2
              }
            },
            "shippingAddress": {
              "country": "US"
            },
            "shippingMode": "Single",
            "shipping": [
            ],
            "taxMode": "Platform",
            "taxRoundingMode": "HalfEven",
            "country": "US",
            "orderState": "Complete",
            "shipmentState": "Shipped",
            "paymentState": "Paid",
            "syncInfo": [
            ],
            "returnInfo": [
            ],
            "discountCodes": [
            ],
            "lastMessageSequenceNumber": 6,
            "cart": {
              "typeId": "cart",
              "id": "d776f1b1-789d-40e0-89d1-f5f33f21739c"
            },
            "inventoryMode": "None",
            "origin": "Customer",
            "taxCalculationMode": "LineItemLevel",
            "itemShippingAddresses": [
            ],
            "refusedGifts": [
            ]
          }
        """
    )
    obj['id'] = uuid_id
    return CTOrder.deserialize(obj)


def gen_order_history(num=1):
    return [gen_order(str(uuid.uuid4())) for _ in range(0, num)]


def gen_example_customer():
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
