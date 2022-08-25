"""
Views for the LMS app
"""

import logging

from edx_rest_framework_extensions.permissions import LoginRedirectIfUnauthenticated
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


class EnrollmentView(APIView):
    """
    API for LMS enrollment.
    """
    permission_classes = [LoginRedirectIfUnauthenticated]
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    throttle_classes = [UserRateThrottle]

    logger.info('LMS app views')
