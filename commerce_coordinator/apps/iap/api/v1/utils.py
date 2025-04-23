"""
Utility functions for handling cart operations such as checking cart status and setting shipping addresses.
"""

import logging
from commercetools.platform.models.cart import CartSetShippingAddressAction
from commercetools.platform.models.common import Address
from commercetools.exceptions import CommercetoolsError

logger = logging.getLogger(__name__)


def is_cart_active(cart) -> bool:
    """
    Check if the cart is in an active state.

    Args:
        cart: The cart object.

    Returns:
        bool: True if the cart is active, False otherwise.
    """
    cart_state = cart.cart_state.value if hasattr(cart.cart_state, "value") else str(cart.cart_state)
    return cart_state.lower() == "active"

def set_shipping_address(cart, shipping_address_data, ct_client):
    """
    Set the shipping address on the cart if not already set.

    Args:
        cart: The cart object.
        shipping_address_data (dict): Shipping address data from request.
        ct_client: Instance of Commercetools API client.

    Returns:
        Updated cart object.

    Raises:
        ValueError: If shipping address data is missing.
        CommercetoolsError: If there is an error updating the cart in Commercetools.
    """

    if not cart.shipping_address:
        if not shipping_address_data:
            raise ValueError("Shipping address is not set in cart or request.")

        address = Address(**shipping_address_data)
        actions = [CartSetShippingAddressAction(address=address)]

        try:
            cart = ct_client.base_client.carts.update_by_id(cart.id, cart.version, actions)
        except CommercetoolsError as err:
            logger.error(
                "[set_shipping_address] Failed to set shipping address for cart %s: error=%s, correlation_id=%s",
                cart.id, err.errors, getattr(err, "correlation_id", None)
            )

        return cart
    return cart
