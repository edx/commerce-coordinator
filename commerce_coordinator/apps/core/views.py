""" Core views. """
import logging
import uuid

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login
from django.db import DatabaseError, connection, transaction
from django.http import Http404, JsonResponse
from django.shortcuts import redirect
from django.views.generic import View
from edx_django_utils.cache import TieredCache
from edx_django_utils.monitoring import ignore_transaction
from rest_framework.views import APIView

from commerce_coordinator.apps.core.constants import Status
from commerce_coordinator.apps.core.memcache import safe_key

logger = logging.getLogger(__name__)
User = get_user_model()
NOTIFICATION_CACHE_TTL_SECS = 60 * 10  # 10 Mins


@transaction.non_atomic_requests
def health(_):
    """Allows a load balancer to verify this service is up.

    Checks the status of the database connection on which this service relies.

    Returns:
        Response: 200 if the service is available, with JSON data indicating the health of each required service
        Response: 503 if the service is unavailable, with JSON data indicating the health of each required service

    Example:
        >>> response = requests.get('https://commerce-coordinator.edx.org/health')
        >>> response.status_code
        200
        >>> response.content
        '{"overall_status": "OK", "detailed_status": {"database_status": "OK", "lms_status": "OK"}}'
    """

    # Ignores health check in performance monitoring so as to not artifically inflate our response time metrics
    ignore_transaction()

    try:
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        cursor.close()
        database_status = Status.OK
    except DatabaseError:
        database_status = Status.UNAVAILABLE

    overall_status = Status.OK if (database_status == Status.OK) else Status.UNAVAILABLE

    data = {
        'overall_status': overall_status,
        'detailed_status': {
            'database_status': database_status,
        },
    }

    if overall_status == Status.OK:
        return JsonResponse(data)
    else:
        return JsonResponse(data, status=503)


class AutoAuth(View):
    """Creates and authenticates a new User with superuser permissions.

    If the ENABLE_AUTO_AUTH setting is not True, returns a 404.
    """

    def get(self, request):
        """
        Create a new User.

        Raises Http404 if auto auth is not enabled.
        """
        if not getattr(settings, 'ENABLE_AUTO_AUTH', None):
            raise Http404

        username_prefix = getattr(settings, 'AUTO_AUTH_USERNAME_PREFIX', 'auto_auth_')

        # Create a new user with staff permissions
        username = password = username_prefix + uuid.uuid4().hex[0:20]
        User.objects.create_superuser(username, email=None, password=password)

        # Log in the new user
        user = authenticate(username=username, password=password)
        login(request, user)

        return redirect('/')


class SingleInvocationAPIView(APIView):
    """APIView that can mark itself as running or not running within TieredCache"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.meta_id = None
        self.meta_view = None
        self.meta_should_mark_not_running = True

    @staticmethod
    def _view_cache_key(view: str, identifier: str) -> str:
        """Get cache key for view and identifier"""
        return safe_key(key=f"{view}_{identifier}", key_prefix="ct_sub_msg_invo", version="1")

    def mark_running(self, view: str, identifier: str, tf=True):
        """Mark view as running or not running"""
        self.set_view(view)
        self.set_identifier(identifier)
        key = SingleInvocationAPIView._view_cache_key(view, identifier)

        if TieredCache.get_cached_response(key).is_found or not tf:
            try:
                TieredCache.delete_all_tiers(key)

            # not all caches throw this but a few do.
            except ValueError as _:  # pragma no cover
                # No-Op, Key not found.
                pass

        if tf:
            TieredCache.set_all_tiers(key, tf, NOTIFICATION_CACHE_TTL_SECS)

    @staticmethod
    def _is_running(view: str, identifier: str):
        """Check if view is running"""
        key = SingleInvocationAPIView._view_cache_key(view, identifier)
        cache_value = TieredCache.get_cached_response(key)
        if cache_value.is_found or cache_value.get_value_or_default(False):
            logger.info(f'[CT-{view}] Currently processing request for %s, ignoring invocation', identifier)
            return True
        return False

    def set_view(self, view: str):
        """Set the view to mark as running"""
        self.meta_view = view

    def set_identifier(self, identifier: str):
        """Set the identifier to mark as running"""
        self.meta_id = identifier

    # Right now we DON'T want to mark the view as not running, unless error.
    # def finalize_response(self, request, response, *args, **kwargs):
    #     tag = self.meta_view
    #     identifier = self.meta_id
    #     if self.meta_should_mark_not_running:
    #         SingleInvocationAPIView.mark_running(tag, identifier, False)
    #     return super().finalize_response(request, response, *args, **kwargs)

    def handle_exception(self, exc):
        """Mark view as not running on exception"""
        tag = self.meta_view
        identifier = self.meta_id
        self.mark_running(tag, identifier, False)
        return super().handle_exception(exc)
