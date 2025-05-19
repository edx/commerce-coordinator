"""
Utils for the InAppPurchase app
"""

import logging
import time

<<<<<<< Updated upstream
from commercetools.platform.models import CentPrecisionMoney, Customer
=======
from commercetools.platform.models import Customer, Money
import jwt
from requests import Session
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
>>>>>>> Stashed changes

from commerce_coordinator.apps.commercetools.catalog_info.constants import EdXFieldNames
from commerce_coordinator.apps.commercetools.clients import CommercetoolsAPIClient
from commerce_coordinator.apps.commercetools.http_api_client import CTCustomAPIClient

APP_STORE_BASE_URL = "https://api.appstoreconnect.apple.com"
IOS_PRODUCT_REVIEW_NOTE = ('This in-app purchase will unlock all the content of the course {course_name}\n\n'
                           'For testing the end-to-end payment flow, please follow the following steps:\n1. '
                           'Go to the Discover tab\n2. Search for "{course_name}"\n3. Enroll in the course'
                           ' "{course_name}"\n4. Hit \"Upgrade to access more features\", it will open a '
                           'detail unlock features page\n5. Hit "Upgrade now for ${course_price}" from the'
                           ' detail page')
logger = logging.getLogger(__name__)


def _get_attributes_to_update(
    *,
    user,
    customer: Customer,
    first_name: str,
    last_name: str,
) -> dict[str, str | None]:
    """
    Get the attributes that need to be updated for the customer.

    Args:
        customer: The existing customer object
        user: The authenticated user from the request

    Returns:
        A dictionary of attributes to update with their new values
    """
    updates = {}

    ct_lms_username = None
    if customer.custom and customer.custom.fields:
        ct_lms_username = customer.custom.fields.get(EdXFieldNames.LMS_USER_NAME)

    if ct_lms_username != user.username:
        updates["lms_username"] = user.username

    if customer.email != user.email:
        updates["email"] = user.email

    if customer.first_name != first_name:
        updates["first_name"] = first_name

    if customer.last_name != last_name:
        updates["last_name"] = last_name

    return updates


def get_email_domain(email: str | None) -> str:
    """Extract the domain from an email address.

    Args:
        email (str): Email address.

    Returns:
        Domain part of the email address.
    """
    return (email or "").lower().strip().partition("@")[-1]


def get_ct_customer(client: CommercetoolsAPIClient, user) -> Customer:
    """
    Get an existing customer for the authenticated user or create a new one.

    Args:
        client: CommercetoolsAPIClient instance
        user: The authenticated user from the request

    Returns:
        The customer object
    """
    customer = client.get_customer_by_lms_user_id(user.lms_user_id)
    first_name, last_name = user.first_name, user.last_name

    if not (first_name and last_name) and user.full_name:
        splitted_name = user.full_name.split(" ", 1)
        first_name = splitted_name[0]
        last_name = splitted_name[1] if len(splitted_name) > 1 else ""

    if customer:
        updates = _get_attributes_to_update(
            user=user,
            customer=customer,
            first_name=first_name,
            last_name=last_name,
        )
        if updates:
            customer = client.update_customer(
                customer=customer,
                updates=updates,
            )
    else:
        customer = client.create_customer(
            email=user.email,
            first_name=first_name,
            last_name=last_name,
            lms_user_id=user.lms_user_id,
            lms_username=user.username,
        )

    return customer


def get_standalone_price_for_sku(sku: str) -> CentPrecisionMoney:
    """
    Get the standalone price for a given SKU.

    Args:
        client: CommercetoolsAPIClient instance
        sku: The SKU of the product

    Returns:
        The standalone price
    """
    api_client = CTCustomAPIClient()

    response = api_client.get_standalone_prices_for_skus([sku])
    if not response or not response[0]:
        message = f"No standalone price found for the SKU: {sku}"
        logger.error(message)
        raise ValueError(message)

    try:
        value = response[0]["value"]
        return CentPrecisionMoney(
            cent_amount=value["centAmount"],
            currency_code=value["currencyCode"],
            fraction_digits=value["fractionDigits"]
        )
    except KeyError as exc:
        message = (
            f"No standalone price found for the SKU: {sku}, received: {response[0]}"
        )
        logger.exception(message, exc_info=exc)
        raise ValueError(message) from exc



def get_auth_headers(configuration):
    """ Get Bearer token with headers to call appstore """

    headers = {
        "kid": configuration['key_id'],
        "typ": "JWT",
        "alg": "ES256"
    }

    payload = {
        "iss": configuration['issuer_id'],
        "exp": round(time.time()) + 60 * 20,  # Token expiration time (20 minutes)
        "aud": "appstoreconnect-v1",
        "bid": configuration['ios_bundle_id']
    }

    private_key = configuration['private_key']
    token = jwt.encode(payload, private_key, algorithm="ES256", headers=headers)
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    return headers

def request_connect_store(url, headers, data=None, method="post"):
    """ Request the given endpoint with multiple tries and backoff time """
    # Adding backoff and retries because of following two reasons
    # 1. In case there is a connection error or server is busy.
    # 2. Product data needs sometime before it gets updated on server for the final submit call,
    # If we submit product right after image uploading it will return 409 error
    # We will try 3 times with backoff time of 1.5, 3, 12 seconds
    retries = Retry(
        total=3,
        backoff_factor=3,
        status_forcelist=[502, 503, 504, 408, 429, 409],
        method_whitelist={'POST', "GET", "PUT", "PATCH"},
    )
    http = Session()
    http.mount('https://', HTTPAdapter(max_retries=retries))
    try:
        if method == "post":
            response = http.post(url, json=data, headers=headers)
        elif method == "patch":
            response = http.patch(url, json=data, headers=headers)
        elif method == "put":
            response = http.put(url, data=data, headers=headers)
        elif method == "get":
            response = http.get(url, headers=headers)
    except requests.RequestException as request_exc:
        raise AppStoreRequestException(request_exc) from request_exc

    return response

def create_inapp_purchase(course, ios_sku, apple_id, headers):
    """ Create in app product and return its id. """

    url = APP_STORE_BASE_URL + "/v2/inAppPurchases"
    data = {
        "data": {
            "type": "inAppPurchases",
            "attributes": {
                "name": course['key'],
                "productId": ios_sku,
                "inAppPurchaseType": "NON_CONSUMABLE",
                "reviewNote": IOS_PRODUCT_REVIEW_NOTE.format(course_name=course['name'],
                                                             course_price=course['price']),
            },
            "relationships": {
                "app": {
                    "data": {
                        "type": "apps",
                        "id": apple_id
                    }
                }
            }
        }
    }
    response = request_connect_store(url=url, data=data, headers=headers)
    if response.status_code == 201:
        return response.json()["data"]["id"]

    raise AppStoreRequestException("Couldn't create inapp purchase id")

def get_or_create_inapp_purchase(ios_stock_record, course, configuration, headers):
    """
    Returns inapp_purchase_id from product attr
    If not present there create a product on ios store and return its inapp_purchase_id
    """

    in_app_purchase_id = getattr(ios_stock_record.product.attr, 'app_store_id', '')
    if not in_app_purchase_id:
        in_app_purchase_id = create_inapp_purchase(course, ios_stock_record.partner_sku,
                                                   configuration['apple_id'], headers)
        ios_stock_record.product.attr.app_store_id = in_app_purchase_id
        ios_stock_record.product.save()

    return in_app_purchase_id

def localize_inapp_purchase(in_app_purchase_id, headers):
    """ Localize given in app product with US locale. """

    url = APP_STORE_BASE_URL + "/v1/inAppPurchaseLocalizations"
    data = {
        "data": {
            "type": "inAppPurchaseLocalizations",
            "attributes": {
                "locale": "en-US",
                "name": "Upgrade Course",
                "description": "Unlock course activities & certificate"
            },
            "relationships": {
                "inAppPurchaseV2": {
                    "data": {
                        "type": "inAppPurchases",
                        "id": in_app_purchase_id
                    }
                }
            }
        }
    }
    response = request_connect_store(url=url, data=data, headers=headers)
    if response.status_code != 201:
        raise AppStoreRequestException("Couldn't localize purchase")

def apply_price_of_inapp_purchase(price, in_app_purchase_id, headers):
    """ Apply price tier to the given in app product. """

    url = APP_STORE_BASE_URL + ("/v2/inAppPurchases/v2/inAppPurchases/{}/pricePoints?filter[territory]=USA"
                                "&include=territory&limit=8000").format(in_app_purchase_id)

    response = request_connect_store(url=url, headers=headers, method='get')
    if response.status_code != 200:
        raise AppStoreRequestException("Couldn't fetch price points")

    # Apple doesn't allow in app price > 1000
    nearest_high_price = nearest_high_price_id = 1001
    for price_point in response.json()['data']:
        customer_price = float(price_point['attributes']['customerPrice'])
        if nearest_high_price > customer_price >= price:
            nearest_high_price = customer_price
            nearest_high_price_id = price_point['id']

    if nearest_high_price == 1001:
        raise AppStoreRequestException("Couldn't find nearest high price point")

    url = APP_STORE_BASE_URL + "/v1/inAppPurchasePriceSchedules"
    data = {
        "data": {
            "type": "inAppPurchasePriceSchedules",
            "attributes": {},
            "relationships": {
                "inAppPurchase": {
                    "data": {
                        "type": "inAppPurchases",
                        "id": in_app_purchase_id
                    }
                },
                "manualPrices": {
                    "data": [
                        {
                            "type": "inAppPurchasePrices",
                            "id": "${price}"
                        }
                    ]
                },
                "baseTerritory": {
                    "data": {
                        "type": "territories",
                        "id": "USA"
                    }
                }
            }
        },
        "included": [
            {
                "id": "${price}",
                "relationships": {
                    "inAppPurchasePricePoint": {
                        "data": {
                            "type": "inAppPurchasePricePoints",
                            "id": nearest_high_price_id
                        }
                    }
                },
                "type": "inAppPurchasePrices",
                "attributes": {
                    "startDate": None
                }
            }
        ]
    }
    response = request_connect_store(url=url, data=data, headers=headers)
    if response.status_code != 201:
        raise AppStoreRequestException("Couldn't apply price")

def upload_screenshot_of_inapp_purchase(in_app_purchase_id, headers):
    """ Upload screenshot for the given product. """
    url = APP_STORE_BASE_URL + "/v1/inAppPurchaseAppStoreReviewScreenshots"
    data = {
        "data": {
            "type": "inAppPurchaseAppStoreReviewScreenshots",
            "attributes": {
                "fileName": "iOS_IAP.png",
                "fileSize": 124790
            },
            "relationships": {
                "inAppPurchaseV2": {
                    "data": {
                        "id": in_app_purchase_id,
                        "type": "inAppPurchases"
                    }
                }
            }
        }
    }

    response = request_connect_store(url, headers, data=data)
    if response.status_code != 201:
        raise AppStoreRequestException("Couldn't get screenshot url")

    response = response.json()
    screenshot_id = response['data']['id']
    url = response['data']['attributes']['uploadOperations'][0]['url']
    with staticfiles_storage.open('images/mobile_ios_product_screenshot.png', 'rb') as image:
        img_headers = {'Content-Type': 'image/png'}
        response = request_connect_store(url, headers=img_headers, data=image.read(), method='put')

        if response.status_code != 200:
            raise AppStoreRequestException("Couldn't upload screenshot")

    url = APP_STORE_BASE_URL + "/v1/inAppPurchaseAppStoreReviewScreenshots/{}".format(screenshot_id)
    data = {
        "data": {
            "type": "inAppPurchaseAppStoreReviewScreenshots",
            "id": screenshot_id,
            "attributes": {
                "uploaded": True,
                "sourceFileChecksum": ""
            }
        }
    }

    response = request_connect_store(url, headers, data=data, method='patch')

    if response.status_code != 200:
        raise AppStoreRequestException("Couldn't finalize screenshot")

def set_territories_of_in_app_purchase(in_app_purchase_id, headers):
    url = APP_STORE_BASE_URL + '/v1/territories?limit=200'
    response = request_connect_store(url, headers, method='get')
    if response.status_code != 200:
        raise AppStoreRequestException("Couldn't fetch territories")

    territories = [{'type': territory['type'], 'id': territory['id']}
                   for territory in response.json()['data']]

    url = APP_STORE_BASE_URL + '/v1/inAppPurchaseAvailabilities'
    data = {
        "data": {
            "type": "inAppPurchaseAvailabilities",
            "attributes": {
                "availableInNewTerritories": True
            },
            "relationships": {
                "availableTerritories": {
                    "data": territories
                },
                "inAppPurchase": {
                    "data": {
                        "id": in_app_purchase_id,
                        "type": "inAppPurchases"
                    }
                }
            }
        }
    }

    response = request_connect_store(url, headers, data=data)

    if response.status_code != 201:
        raise AppStoreRequestException("Couldn't modify territories of inapp purchase")

def submit_in_app_purchase_for_review(in_app_purchase_id, headers):
    """ Submit in app purchase for the final review by appstore. """
    url = APP_STORE_BASE_URL + "/v1/inAppPurchaseSubmissions"
    data = {
        "data": {
            "type": "inAppPurchaseSubmissions",
            "relationships": {
                "inAppPurchaseV2": {
                    "data": {
                        "type": "inAppPurchases",
                        "id": in_app_purchase_id
                    }
                }
            }
        }
    }
    response = request_connect_store(url=url, data=data, headers=headers)
    if response.status_code != 201:
        raise AppStoreRequestException("Couldn't submit purchase")

def create_ios_product(course, ios_product, configuration):
    """
    Create in app ios product on connect store.
    return error message in case of failure.
    """
    if course['price'] > 1000:
        return 'Error: Appstore does not allow price > 1000'

    headers = get_auth_headers(configuration)
    try:
        in_app_purchase_id = get_or_create_inapp_purchase(ios_product, course, configuration, headers)
        localize_inapp_purchase(in_app_purchase_id, headers)
        apply_price_of_inapp_purchase(course['price'], in_app_purchase_id, headers)
        upload_screenshot_of_inapp_purchase(in_app_purchase_id, headers)
        set_territories_of_in_app_purchase(in_app_purchase_id, headers)
        return submit_in_app_purchase_for_review(in_app_purchase_id, headers)
    except AppStoreRequestException as store_exception:
        error_msg = "[%s]  for course [%s] with sku [%s]" % (str(store_exception), course['key'],
                                                             ios_product.partner_sku)
        logger.error(error_msg)
        return error_msg


class AppStoreRequestException(Exception):
    pass
