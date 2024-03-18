"""
Django REST Framework authentication classes.
"""

from edx_rest_framework_extensions.auth.jwt.authentication import JwtAuthentication
from rest_framework_jwt.compat import smart_str


class JwtBearerAuthentication(JwtAuthentication):
    """
    Class to ignore JWT_AUTH_HEADER_PREFIX, using ``Bearer`` instead.

    The Open edX platform defaults to an authorization header like:

        Authorization: JWT <jwt-token>

    We do this by setting JWT_AUTH_HEADER_PREFIX to ``Bearer``.

    However, most OAuth2 implementations use an authorization header like:

        Authorization: Bearer <jwt-token>

    This class allows us to default to the former, but selectively choose
    Django REST Framework views where we can ignore JWT_AUTH_HEADER_PREFIX and
    expect ``Bearer`` instead for the latter, by adding this class as one of
    the ``authentication_classes`` of the view.

    See: https://styria-digital.github.io/django-rest-framework-jwt/#jwt_auth_header_prefix
    See: https://github.com/Styria-Digital/django-rest-framework-jwt/blob/4e8550e15902399df277aac97e6f300a0610697f/CHANGELOG.md?plain=1#L356  # pylint: disable=line-too-long # noqa: E501
    """

    @classmethod
    def prefixes_match(cls, prefix):
        """
        Check to see if prefix is ``bearer`` (instead of JWT_AUTH_HEADER_PREFIX).

        Overrides the following implementation:

        https://github.com/Styria-Digital/django-rest-framework-jwt/blob/4e8550e15902399df277aac97e6f300a0610697f/src/rest_framework_jwt/authentication.py#L117
        """
        return smart_str(prefix.lower()) == 'bearer'
