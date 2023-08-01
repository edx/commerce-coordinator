""" Secondary Auth Classes """

from django.http.request import HttpHeaders
from edx_rest_framework_extensions.auth.jwt.authentication import JwtAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_jwt.settings import api_settings as rest_api_settings


class ForceCookieJwtAuthentication(JwtAuthentication):
    """
    Force JWT Authentication from edX Auth Cookies but forging a `JWT` Bearer token from those cookies

    A good example of why to use this can be found in `THES-236`, however, the basic reason is this:
    LMS just FORWARDS to CC via a browser, it doesn't set a body, nor does it customize headers, and thus we are not
    able to make it use the `Use-Jwt-Cookie` (edx_rest_framework_extensions.auth.jwt.constants.USE_JWT_COOKIE_HEADER)
    nor can we limit it from wanting an HTML resource.
    """

    def authenticate(self, request):
        # dfr is a touch ridiculous; it pulls headers from the environment, prefixed with `HTTP_`
        cookie_prefix = rest_api_settings.JWT_AUTH_COOKIE
        jwt_hdr_payload_cookie_name = cookie_prefix + '-header-payload'
        jwt_sig_cookie_name = cookie_prefix + '-signature'

        if jwt_hdr_payload_cookie_name not in request.COOKIES or jwt_sig_cookie_name not in request.COOKIES:
            raise AuthenticationFailed('Authentication Cookie Missing')

        # Forge a `JWT` Bearer Token
        request.META['HTTP_AUTHORIZATION'] = 'JWT ' + request.COOKIES[jwt_hdr_payload_cookie_name] + '.' \
                                             + request.COOKIES[jwt_sig_cookie_name]
        request.headers = HttpHeaders(request.META)

        return super().authenticate(request)
