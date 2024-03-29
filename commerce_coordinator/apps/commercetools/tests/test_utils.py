"""
Tests for Commerce tools utils
"""
import unittest
from unittest.mock import MagicMock

from braze.client import BrazeClient
from django.conf import settings
from django.test import override_settings
from django.urls import reverse
from mock import Mock, patch

from commerce_coordinator.apps.commercetools.tests.conftest import gen_order
from commerce_coordinator.apps.commercetools.tests.constants import EXAMPLE_FULFILLMENT_SIGNAL_PAYLOAD
from commerce_coordinator.apps.commercetools.utils import (
    extract_ct_order_information_for_braze_canvas,
    extract_ct_product_information_for_braze_canvas,
    get_braze_client,
    send_order_confirmation_email
)


class TestBrazeHelpers(unittest.TestCase):
    """
    Tests for Braze Utils class
    """

    @override_settings(
        BRAZE_API_KEY="braze_api_key",
        BRAZE_API_SERVER="braze_api_server"
    )
    def test_get_braze_client_with_valid_settings(self):
        braze_client = get_braze_client()

        # Assert that a BrazeClient instance is returned
        self.assertIsNotNone(braze_client)
        self.assertIsInstance(braze_client, BrazeClient)

    @override_settings(
        BRAZE_API_SERVER="braze_api_server"
    )
    def test_get_braze_client_with_missing_api_key(self):
        braze_client = get_braze_client()

        # Assert that None is returned when API key is missing
        self.assertIsNone(braze_client)

    @override_settings(
        BRAZE_API_KEY="braze_api_key",
    )
    def test_get_braze_client_with_missing_api_server(self):
        braze_client = get_braze_client()

        # Assert that None is returned when API server is missing
        self.assertIsNone(braze_client)

    def test_get_braze_client_with_missing_settings(self):
        braze_client = get_braze_client()

        # Assert that None is returned when both API key and API server are missing
        self.assertIsNone(braze_client)

    @override_settings(
        BRAZE_API_KEY="braze_api_key",
        BRAZE_API_SERVER="braze_api_server",
        BRAZE_CT_ORDER_CONFIRMATION_CANVAS_ID="dummy_canvas"
    )
    @patch('commerce_coordinator.apps.commercetools.utils.get_braze_client')
    def test_send_order_confirmation_email_success(self, mock_get_braze_client):
        mock_braze_client = Mock()
        mock_get_braze_client.return_value = mock_braze_client

        canvas_entry_properties = {}
        lms_user_id = 'user123'
        lms_user_email = 'user@example.com'

        with patch.object(mock_braze_client, 'send_canvas_message') as mock_send_canvas_message:
            send_order_confirmation_email(
                lms_user_id, lms_user_email, canvas_entry_properties
            )

            mock_send_canvas_message.assert_called_once_with(
                canvas_id='dummy_canvas',
                recipients=[{"external_user_id": lms_user_id, "attributes": {"email": lms_user_email}}],
                canvas_entry_properties=canvas_entry_properties,
            )

    @override_settings(
        BRAZE_API_KEY="braze_api_key",
        BRAZE_API_SERVER="braze_api_server",
        BRAZE_CT_ORDER_CONFIRMATION_CANVAS_ID="dummy_canvas"
    )
    @patch('commerce_coordinator.apps.commercetools.utils.get_braze_client')
    @patch('commerce_coordinator.apps.commercetools.utils.logger.exception')
    def test_send_order_confirmation_email_failure(self, mock_logger, mock_get_braze_client):
        mock_braze_client = Mock()
        mock_get_braze_client.return_value = mock_braze_client

        canvas_entry_properties = {}
        lms_user_id = 'user123'
        lms_user_email = 'user@example.com'

        with patch.object(mock_braze_client, 'send_canvas_message') as mock_send_canvas_message:
            mock_send_canvas_message.side_effect = Exception('Error sending Braze email')
            send_order_confirmation_email(
                lms_user_id, lms_user_email, canvas_entry_properties
            )

            mock_send_canvas_message.assert_called_once_with(
                canvas_id='dummy_canvas',
                recipients=[{"external_user_id": lms_user_id, "attributes": {"email": lms_user_email}}],
                canvas_entry_properties=canvas_entry_properties,
            )
            mock_logger.assert_called_once_with('Encountered exception sending Order confirmation email. '
                                                'Exception: Error sending Braze email')

    def test_extract_ct_product_information_for_braze_canvas(self):
        order = gen_order(EXAMPLE_FULFILLMENT_SIGNAL_PAYLOAD['order_number'])
        line_item = order.line_items[0]
        result = extract_ct_product_information_for_braze_canvas(line_item)
        expected = {
            'duration': '4-5 Weeks',
            'image_url': 'https://90bbf3dd6df9e8673f39-65625168de2b7f206447b8dd2ec7c899.ssl.cf1.rackcdn.com/image%20'
                         '(47)-4DyzF3NF.png',
            'partner_name': 'MichiganX',
            'price': '$49.00',
            'start_date': '2021-04-19',
            'title': 'Injury Prevention for Children & Teens',
            'type': 'course'
        }
        assert result == expected

    @override_settings(
        LMS_DASHBOARD_URL="https://lms.example.com",
    )
    def test_extract_ct_order_information_for_braze_canvas_with_discount(self):
        order = gen_order(EXAMPLE_FULFILLMENT_SIGNAL_PAYLOAD['order_number'])
        customer = MagicMock()
        customer.first_name = 'Test'
        customer.last_name = 'User'
        customer.email = 'test@example.com'
        result = extract_ct_order_information_for_braze_canvas(customer, order)
        expected = {
            "first_name": "Test",
            "last_name": "User",
            "redirect_url": settings.LMS_DASHBOARD_URL,
            "view_receipt_cta_url": f"{settings.COMMERCE_COORDINATOR_URL}"
                                    f"{reverse('frontend_app_ecommerce:order_receipt')}?order_number={order.id}",
            "purchase_date": 'Oct 31, 2023',
            "purchase_time": '07:56 PM (UTC)',
            "subtotal": "$74.00",
            "total": "$49.00",
            'discount_code': 'TEST_DISCOUNT_CODE',
            'discount_value': '$25.00'
        }
        assert result == expected

    @override_settings(
        LMS_DASHBOARD_URL="https://lms.example.com",
    )
    def test_extract_ct_order_information_for_braze_canvas_without_discount(self):
        order = gen_order(EXAMPLE_FULFILLMENT_SIGNAL_PAYLOAD['order_number'], with_discount=False)
        customer = MagicMock()
        customer.first_name = 'Test'
        customer.last_name = 'User'
        customer.email = 'test@example.com'
        result = extract_ct_order_information_for_braze_canvas(customer, order)
        expected = {
            "first_name": "Test",
            "last_name": "User",
            "redirect_url": settings.LMS_DASHBOARD_URL,
            "view_receipt_cta_url": f"{settings.COMMERCE_COORDINATOR_URL}"
                                    f"{reverse('frontend_app_ecommerce:order_receipt')}?order_number={order.id}",
            "purchase_date": 'Oct 31, 2023',
            "purchase_time": '07:56 PM (UTC)',
            "subtotal": "$149.00",
            "total": "$149.00",
        }
        assert result == expected
