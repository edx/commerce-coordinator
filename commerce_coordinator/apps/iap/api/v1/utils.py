from typing import Optional
from commercetools.platform.models import Customer, Money

from commerce_coordinator.apps.commercetools.catalog_info.constants import (
    EdXFieldNames,
)
from commerce_coordinator.apps.commercetools.clients import CommercetoolsAPIClient
from commerce_coordinator.apps.commercetools.http_api_client import CTCustomAPIClient
from commerce_coordinator.apps.core.segment import track


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


def get_standalone_price_for_sku(sku: str) -> Money:
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
        raise ValueError(f"No standalone price found for the SKU: {sku}")

    try:
        value = response[0]["value"]
        return Money(
            cent_amount=value["centAmount"],
            currency_code=value["currencyCode"],
        )
    except KeyError as exc:
        raise ValueError(
            f"No standalone price found for the SKU: {sku}, received: {response[0]}"
        ) from exc

def sum_money(*args: Optional[dict[str, any]]) -> dict[str, any]:
    """
    Sums a list of amount dicts.

    Args: dict (centAmount, currencyCode, fractionDigits)

    Returns a dict with total centAmount and shared fractionDigits and currencyCode.
    """

    amount_list = [amount for amount in args if amount]

    
    total_cent_amount = sum(amount.get("centAmount", 0) for amount in amount_list)

def cent_to_dollars(amount: dict) -> float:
    """
    Get converted amount in dollars from cents upto fraction digits in points.

    Args:
       amount: dict (centAmount, fractionDigits)

    Returns:
        The converted amount in dollars
    """

    cent_amount = amount.get("centAmount", 0)
    fraction_digits = amount.get('fractionDigits', 2)

    return cent_amount / (10 ** fraction_digits)


def emit_checkout_started_event(lms_user_id, cart_id, currency_code):
    
    """
    Triggering Checkout Started event on segment.
    """
    event_props = {
        "cart_id": cart_id,
        "checkout_id": cart_id,
        "currency": currency_code,
        "revenue": amount_with_tax,
        "value": gross_amount,
        "coupon": discount_code,
        "discount": discount_in_dollars,
        "products": products,
        "is_mobile": True
    }

    track(
        lms_user_id=lms_user_id,
        event='Checkout Started',
        properties=event_props
    )
