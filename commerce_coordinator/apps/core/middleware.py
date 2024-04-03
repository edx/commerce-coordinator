"""
Middleware for Commerce Coordinator.
"""
import logging

from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def log_drf_exceptions(exc, context):
    """
    Log Django REST Framework exceptions.
    """
    response = exception_handler(exc, context)

    status_code = None
    if response:
        status_code = response.status_code

    view_name = None
    if context and 'view' in context:
        view_type = type(context['view'])
        view_name = view_type.__module__ + '.' + view_type.__qualname__

    exception_type = None
    if exc:
        exception_type = type(exc).__module__ + '.' + type(exc).__qualname__

    method = path = query_params = data = None
    if context and 'request' in context:
        request = context['request']
        method = request.method
        path = request.get_full_path_info()
        query_params = request.query_params
        data = request.data

    logger.warning(
        'DRF Exception in APIView: status code: [%s] on view: [%s] of ' \
        'type: [%s], via [%s] on path: [%s] with exception: [%s].',
        status_code, view_name, exception_type, method, path, exc,
    )
    logger.debug(
        'Context for DRF Exception in APIView: status code: [%s] on ' \
        'view: [%s] of type: [%s], via [%s] on path: [%s] with exception: [%s], ' \
        'from request query_params: [%s], and data: [%s].',
        status_code, view_name, exception_type, method, path, exc,
        query_params, data
    )

    return response
