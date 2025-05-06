from commercetools.platform.models import Customer

from commerce_coordinator.apps.commercetools.catalog_info.constants import (
    EdXFieldNames,
)
from commerce_coordinator.apps.commercetools.clients import CommercetoolsAPIClient


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
