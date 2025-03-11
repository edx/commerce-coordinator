"""
Configuration settings via waffle flags for redirecting to CommerceTools.
"""

import waffle  # pylint: disable=invalid-django-waffle-import

WAFFLE_FLAG_NAMESPACE = "transition_to_commercetools"

REDIRECT_TO_COMMERCETOOLS_CHECKOUT = f'{WAFFLE_FLAG_NAMESPACE}.redirect_to_commercetools_checkout'


def is_redirect_to_commercetools_enabled_for_user(request):
    """
    Check if REDIRECT_TO_COMMERCETOOLS_CHECKOUT flag is enabled.
    """
    return waffle.flag_is_active(request, REDIRECT_TO_COMMERCETOOLS_CHECKOUT)
