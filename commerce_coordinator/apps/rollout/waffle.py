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


def is_program_redirection_to_ct_enabled(request):
    """
    Check if PROGRAM_CT_REDIRECTION flag is enabled.
    """
    return waffle.flag_is_active(request, "PROGRAM_CT_REDIRECTION")
