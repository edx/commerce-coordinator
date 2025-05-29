"""
Utils for the InAppPurchase app
"""

import logging
from decimal import Decimal

from commercetools.platform.models import CentPrecisionMoney, Customer
from iso4217 import Currency

from commerce_coordinator.apps.commercetools.catalog_info.constants import EdXFieldNames
from commerce_coordinator.apps.commercetools.clients import CommercetoolsAPIClient
from commerce_coordinator.apps.commercetools.http_api_client import CTCustomAPIClient

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
            fraction_digits=value["fractionDigits"],
        )
    except KeyError as exc:
        message = (
            f"No standalone price found for the SKU: {sku}, received: {response[0]}"
        )
        logger.exception(message, exc_info=exc)
        raise ValueError(message) from exc


def convert_localized_price_to_ct_cent_amount(
    *,
    amount: int | Decimal,
    currency_code: str,
    exponent=0,
) -> int:
    """Convert a localized price to Commercetools cent amount.

    Args:
        amount: The amount to convert.
        currency: The currency code (ISO 4217).
        exponent: The exponent indicating how many decimal places the passed
        amount is scaled by (e.g., 2 for centAmount). Defaults to 0.

    Returns:
        int: The amount in Commercetools cent format.
    """
    fraction_digits = Currency(currency_code).exponent or 0

    return int(Decimal(amount).scaleb(fraction_digits - exponent))
