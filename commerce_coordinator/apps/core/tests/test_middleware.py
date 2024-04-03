"""Tests for middleware.py"""
from django.http import Http404
from rest_framework import serializers
from rest_framework.decorators import api_view
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory, APITestCase

from ..middleware import log_drf_exceptions
from ..serializers import CoordinatorSerializer


class LogDRFExceptionsTests(APITestCase):
    """Tests for log_drf_exceptions() middleware."""

    def setUp(self):
        """Test setup."""

        self.factory = APIRequestFactory()
        self.uut = log_drf_exceptions

    def test_invalid_serializer_logs(self):
        """Check that an invalid serializer produces logs."""

        class MockSerializer(CoordinatorSerializer):
            """An example serializer that accepts a char and an int."""
            char = serializers.CharField(required=True)
            integer = serializers.IntegerField(required=True)

        @api_view()
        def mock_view_with_invalid_serializer(request):
            """A mock view that runs the request's data through the MockSerializer."""
            serializer = MockSerializer(data=request.query_params)
            serializer.is_valid(raise_exception=True)
            return Response()

        # Simulate request/response...

        # For request with no errors, no logs emitted:
        with self.assertNoLogs(self.uut.__module__):
            request = self.factory.get('/test', data={
                'char': 'a-string',
                'integer': 1
            })
            mock_view_with_invalid_serializer(request)

        # For request with an error, warning emitted:
        with self.assertLogs(self.uut.__module__, 'WARNING') as log_manager:
            request = self.factory.get('/test', data={
                'char': 'a-string',
                'integer': 'not-an-integer'  # Should be a number, not a string.
            })
            mock_view_with_invalid_serializer(request)
        print(log_manager.output)
        self.assertEqual(log_manager.records[0].funcName, self.uut.__name__)

    def test_404_throw_logs(self):
        """Check that an explicit throw yields logs."""

        @api_view()
        def mock_view_with_404(request):
            """A mock view that throws a 404."""
            raise Http404()

        # For request with an error, warning emitted:
        with self.assertLogs(self.uut.__module__, 'WARNING') as log_manager:
            request = self.factory.get('/test')
            mock_view_with_404(request)
        print(log_manager.output)
        self.assertEqual(log_manager.records[0].funcName, self.uut.__name__)

    def test_generic_exception_raise_logs(self):
        """Check that an explicit throw yields logs."""

        @api_view()
        def mock_view_raises_generic_exception(request):
            """A mock view that raises a generic Exception."""
            raise APIException()

        # For request with an error, warning emitted:
        with self.assertLogs(self.uut.__module__, 'WARNING') as log_manager:
            request = self.factory.get('/test')
            mock_view_raises_generic_exception(request)
        print(log_manager.output)
        self.assertEqual(log_manager.records[0].funcName, self.uut.__name__)
