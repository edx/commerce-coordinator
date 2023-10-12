import json
import typing

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
def gen_order_history():
    return [
        CTOrder.deserialize(json.loads(
            """
              {
                "id": "582f52db-a084-4669-b60c-a82d5b6a4b60",
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
                          "name": "edx-course_run_search_text",
                          "value": {
                            "en": "05cfefe9-8eae-41e0-8e44-52a2144668af\nDemonstration Course\n\nhttp://edx.devstack.lms:18000/course/demonstration-course-course-v1-edx-demox-demo-course\n\n    edX: \n\ninstructor_paced\n\n",
                            "en-US": "05cfefe9-8eae-41e0-8e44-52a2144668af\nDemonstration Course\n\nhttp://edx.devstack.lms:18000/course/demonstration-course-course-v1-edx-demox-demo-course\n\n    edX: \n\ninstructor_paced\n\n"
                          }
                        },
                        {
                          "name": "edx-parent_course_search_text",
                          "value": {
                            "en": "142765f0-7c1e-4ac4-93fe-8516d87f985e\nDemonstration Course\n\nhttp://edx.devstack.lms:18000/course/None\n\n    edX: \n\n    course-v1:edX+DemoX+Demo_Course: Demonstration Course\n\n",
                            "en-US": "142765f0-7c1e-4ac4-93fe-8516d87f985e\nDemonstration Course\n\nhttp://edx.devstack.lms:18000/course/None\n\n    edX: \n\n    course-v1:edX+DemoX+Demo_Course: Demonstration Course\n\n"
                          }
                        },
                        {
                          "name": "edx-course_json",
                          "value": "{\"availability\": [\"Current\"], \"card_image_url\": \"https://theseus.sandbox.edx.org/asset-v1:edX+DemoX+Demo_Course+type@asset+block@images_course_image.jpg\", \"course_runs\": [\"course-v1:edX+DemoX+Demo_Course\"], \"expected_learning_items\": [], \"end\": [null], \"course_ends\": \"Future\", \"end_date\": null, \"enrollment_start\": [\"2013-02-05T00:00:00+00:00\"], \"enrollment_end\": [null], \"first_enrollable_paid_seat_price\": null, \"languages\": [], \"modified\": \"2023-03-20T17:57:21.994755+00:00\", \"prerequisites\": [], \"skill_names\": [], \"skills\": [], \"status\": [\"published\"], \"start\": [\"2013-02-05T05:00:00+00:00\"], \"course_type\": \"verified-audit\", \"enterprise_subscription_inclusion\": false, \"course_length\": \"\", \"external_course_marketing_type\": null, \"product_source\": null, \"authoring_organizations\": [\"edX: \"], \"authoring_organization_bodies\": [\"{\\\"uuid\\\": \\\"09b980e7-6bcc-4687-9dce-44adeae36710\\\", \\\"key\\\": \\\"edX\\\", \\\"name\\\": \\\"\\\", \\\"auto_generate_course_run_keys\\\": true, \\\"certificate_logo_image_url\\\": null, \\\"logo_image_url\\\": null, \\\"organization_hex_color\\\": null, \\\"description\\\": null, \\\"description_es\\\": \\\"\\\", \\\"homepage_url\\\": null, \\\"tags\\\": [], \\\"marketing_url\\\": \\\"http://edx.devstack.lms:18000/school/edx\\\", \\\"slug\\\": \\\"edx\\\", \\\"banner_image_url\\\": null, \\\"enterprise_subscription_inclusion\\\": false}\"], \"key\": \"edX+DemoX\", \"title\": \"Demonstration Course\", \"full_description\": null, \"image_url\": \"https://theseus.sandbox.edx.org/asset-v1:edX+DemoX+Demo_Course+type@asset+block@images_course_image.jpg\", \"logo_image_urls\": [], \"level_type\": null, \"partner\": \"edx\", \"outcome\": null, \"org\": \"edX\", \"subject_uuids\": [], \"short_description\": null, \"seat_types\": [\"verified\", \"audit\"], \"subjects\": [], \"sponsoring_organizations\": [], \"aggregation_key\": \"course:edX+DemoX\", \"content_type\": \"course\", \"id\": \"course_metadata.course.1\", \"organizations\": [\"edX: \"], \"pk\": 1, \"text\": \"142765f0-7c1e-4ac4-93fe-8516d87f985e\\nDemonstration Course\\n\\n\\n\\nhttp://edx.devstack.lms:18000/course/None\\n\\n\\n\\n\\n\\n\\n    edX: \\n\\n\\n\\n\\n\\n\\n\\n\\n\\n\\n\\n\\n\\n    course-v1:edX+DemoX+Demo_Course: Demonstration Course\\n\\n\", \"uuid\": \"142765f0-7c1e-4ac4-93fe-8516d87f985e\"}"
                        },
                        {
                          "name": "edx-course_run_json",
                          "value": "{\"announcement\": null, \"availability\": \"Current\", \"authoring_organization_uuids\": [\"09b980e7-6bcc-4687-9dce-44adeae36710\"], \"course_key\": \"edX+DemoX\", \"end\": null, \"enrollment_start\": \"2013-02-05T00:00:00+00:00\", \"enrollment_end\": null, \"first_enrollable_paid_seat_sku\": \"8CF08E5\", \"go_live_date\": null, \"has_enrollable_seats\": true, \"has_enrollable_paid_seats\": true, \"hidden\": false, \"is_enrollable\": true, \"is_current_and_still_upgradeable\": true, \"language\": null, \"license\": \"\", \"marketing_url\": \"http://edx.devstack.lms:18000/course/demonstration-course-course-v1-edx-demox-demo-course\", \"min_effort\": null, \"max_effort\": null, \"mobile_available\": false, \"number\": \"DemoX\", \"paid_seat_enrollment_end\": \"2024-03-19T17:52:43.355363+00:00\", \"pacing_type\": \"instructor_paced\", \"program_types\": [], \"published\": true, \"skill_names\": [], \"skills\": [], \"status\": \"published\", \"start\": \"2013-02-05T05:00:00+00:00\", \"slug\": \"demonstration-course-course-v1-edx-demox-demo-course\", \"staff_uuids\": [], \"type\": \"verified\", \"transcript_languages\": [], \"weeks_to_complete\": null, \"authoring_organizations\": [\"edX: \"], \"authoring_organization_bodies\": [\"{\\\"uuid\\\": \\\"09b980e7-6bcc-4687-9dce-44adeae36710\\\", \\\"key\\\": \\\"edX\\\", \\\"name\\\": \\\"\\\", \\\"auto_generate_course_run_keys\\\": true, \\\"certificate_logo_image_url\\\": null, \\\"logo_image_url\\\": null, \\\"organization_hex_color\\\": null, \\\"description\\\": null, \\\"description_es\\\": \\\"\\\", \\\"homepage_url\\\": null, \\\"tags\\\": [], \\\"marketing_url\\\": \\\"http://edx.devstack.lms:18000/school/edx\\\", \\\"slug\\\": \\\"edx\\\", \\\"banner_image_url\\\": null, \\\"enterprise_subscription_inclusion\\\": false}\"], \"key\": \"course-v1:edX+DemoX+Demo_Course\", \"title\": \"Demonstration Course\", \"first_enrollable_paid_seat_price\": 149, \"full_description\": null, \"image_url\": \"https://theseus.sandbox.edx.org/asset-v1:edX+DemoX+Demo_Course+type@asset+block@images_course_image.jpg\", \"logo_image_urls\": [], \"level_type\": null, \"partner\": \"edx\", \"outcome\": null, \"org\": \"edX\", \"subject_uuids\": [], \"short_description\": null, \"seat_types\": [\"verified\", \"audit\"], \"subjects\": [], \"sponsoring_organizations\": [], \"aggregation_key\": \"courserun:edX+DemoX\", \"content_type\": \"courserun\", \"id\": \"course_metadata.courserun.1\", \"organizations\": [\"edX: \"], \"pk\": 1, \"text\": \"05cfefe9-8eae-41e0-8e44-52a2144668af\\nDemonstration Course\\n\\n\\n\\nhttp://edx.devstack.lms:18000/course/demonstration-course-course-v1-edx-demox-demo-course\\n\\n\\n\\n\\n\\n\\n    edX: \\n\\n\\n\\n\\n\\n\\n\\n\\n\\n\\n\\n\\ninstructor_paced\\n\\n\\n\\n\\n\\n\", \"uuid\": \"05cfefe9-8eae-41e0-8e44-52a2144668af\"}"
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
        ))
    ]


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
              "edx-lms_user_id": 17
            }
          },
          "salutation": "",
          "stores": [
          ],
          "authenticationMode": "Password"
        }
        """
    ))
