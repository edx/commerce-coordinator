"""
Configuration settings via waffle flags for redirecting to CommerceTools.
"""

import waffle  # pylint: disable=invalid-django-waffle-import

WAFFLE_FLAG_NAMESPACE = "transition_to_commercetools"

REDIRECT_TO_COMMERCETOOLS_CHECKOUT = f'{WAFFLE_FLAG_NAMESPACE}.redirect_to_commercetools_checkout'

PROGRAM_REDIRECT_TO_COMMERCETOOLS_CHECKOUT = f'{WAFFLE_FLAG_NAMESPACE}.program_redirect_to_commercetools_checkout'

ORDER_FULFILLMENT_SERVICE_REDIRECTION_ENABLED = f'{WAFFLE_FLAG_NAMESPACE}.order_fulfillment_service_redirection_enabled'


def is_redirect_to_commercetools_enabled_for_user(request):
    """
    Check if REDIRECT_TO_COMMERCETOOLS_CHECKOUT flag is enabled.
    """
    return waffle.flag_is_active(request, REDIRECT_TO_COMMERCETOOLS_CHECKOUT)


def is_program_redirection_to_ct_enabled(request):
    """
    Check if the PROGRAM_REDIRECT_TO_COMMERCETOOLS_CHECKOUT flag is enabled.
    """
    return waffle.flag_is_active(request, PROGRAM_REDIRECT_TO_COMMERCETOOLS_CHECKOUT)


def is_order_fulfillment_service_redirection_enabled(request):
    """
    Check if fulfill_order_placed_message_signal_task redirects to order fulfiment service

    """
    return waffle.flag_is_active(request, ORDER_FULFILLMENT_SERVICE_REDIRECTION_ENABLED)
