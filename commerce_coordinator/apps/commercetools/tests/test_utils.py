"""
Tests for Commerce tools utils
"""
import hashlib
import unittest
from unittest.mock import MagicMock

import ddt
import pytest
import requests_mock
from braze.client import BrazeClient
from commercetools.platform.models import TransactionState, TransactionType
from django.conf import settings
from django.test import override_settings
from django.urls import reverse
from mock import Mock, patch

from commerce_coordinator.apps.commercetools.catalog_info.edx_utils import get_edx_lms_user_name
from commerce_coordinator.apps.commercetools.tests.conftest import (
    gen_example_customer,
    gen_order,
    gen_payment,
    gen_payment_with_multiple_transactions
)
from commerce_coordinator.apps.commercetools.tests.constants import EXAMPLE_FULFILLMENT_SIGNAL_PAYLOAD
from commerce_coordinator.apps.commercetools.utils import (
    create_retired_fields,
    create_zendesk_ticket,
    extract_ct_order_information_for_braze_canvas,
    extract_ct_product_information_for_braze_canvas,
    get_braze_client,
    has_full_refund_transaction,
    has_refund_transaction,
    send_order_confirmation_email,
    send_refund_notification,
    translate_stripe_refund_status_to_transaction_status
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
                                    f"{reverse('frontend_app_ecommerce:order_receipt')}"
                                    f"?order_number={order.order_number}",
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
                                    f"{reverse('frontend_app_ecommerce:order_receipt')}"
                                    f"?order_number={order.order_number}",
            "purchase_date": 'Oct 31, 2023',
            "purchase_time": '07:56 PM (UTC)',
            "subtotal": "$149.00",
            "total": "$149.00",
        }
        assert result == expected


class TestHasRefundTransaction(unittest.TestCase):
    """
    Tests for Has Refund Transaction Utils class
    """

    def test_has_refund_transaction_with_refund(self):
        payment = gen_payment()
        self.assertTrue(has_refund_transaction(payment))

    def test_has_refund_transaction_without_refund(self):
        payment = gen_payment()
        payment.transactions[0].type = TransactionType.CHARGE
        self.assertFalse(has_refund_transaction(payment))


class TestHasFullRefundTransaction(unittest.TestCase):
    """
    Tests for Has Full Refund Transaction Utils function
    """

    def test_has_full_refund_transaction_with_full_refund(self):
        payment = gen_payment_with_multiple_transactions(TransactionType.CHARGE, 4900, TransactionType.REFUND, 4900)
        self.assertTrue(has_full_refund_transaction(payment))

    def test_has_partial_refund_transaction(self):
        payment = gen_payment_with_multiple_transactions(TransactionType.CHARGE, 4900, TransactionType.REFUND, 2500)
        self.assertFalse(has_full_refund_transaction(payment))

    def test_has_no_refund_transaction(self):
        payment = gen_payment_with_multiple_transactions(TransactionType.CHARGE, 4900)
        self.assertFalse(has_full_refund_transaction(payment))


class TestTranslateStripeRefundStatus(unittest.TestCase):
    """
    Tests for Translating Stripes Refund Status Utils class
    """

    def test_translate_stripe_refund_status_succeeded(self):
        self.assertEqual(translate_stripe_refund_status_to_transaction_status('succeeded'), TransactionState.SUCCESS)

    def test_translate_stripe_refund_status_pending(self):
        self.assertEqual(translate_stripe_refund_status_to_transaction_status('pending'), TransactionState.PENDING)

    def test_translate_stripe_refund_status_failed(self):
        self.assertEqual(translate_stripe_refund_status_to_transaction_status('failed'), TransactionState.FAILURE)

    def test_translate_stripe_refund_status_other(self):
        # Test for an unknown status
        self.assertEqual(translate_stripe_refund_status_to_transaction_status('unknown_status'), 'unknown_status')


@pytest.mark.django_db
@ddt.ddt
class TestSendRefundNotification(unittest.TestCase):
    """
    Tests for creating of and sending Zendesk tickets
    """

    def setUp(self):
        self.order = gen_order(EXAMPLE_FULFILLMENT_SIGNAL_PAYLOAD['order_number'], with_discount=False)
        self.user = gen_example_customer()

    @patch("commerce_coordinator.apps.commercetools.utils.create_zendesk_ticket")
    def test_commercetools_refund_send_notification_failed(self, mock_create_zendesk_ticket):
        mock_create_zendesk_ticket.return_value = False

        self.assertFalse(send_refund_notification(self.user, self.order.order_number))

    @patch("commerce_coordinator.apps.commercetools.utils.create_zendesk_ticket")
    def test_commercetools_refund_send_notification_success(self, mock_create_zendesk_ticket):
        mock_create_zendesk_ticket.return_value = True

        self.assertTrue(send_refund_notification(self.user, self.order.order_number))

    @patch('commerce_coordinator.apps.commercetools.utils.logger.error')
    def test_create_zendesk_ticket_failed_not_configured(self, mock_logger):
        tags = 'test_tags'
        subject = 'test_subject'
        body = 'test_body'

        create_zendesk_ticket(
            get_edx_lms_user_name(self.user),
            self.user.email,
            subject,
            body,
            tags
        )

        mock_logger.assert_called_once_with('Zendesk is not configured. Cannot create a ticket.')

    @override_settings(
            ZENDESK_URL="https://test_url",
            ZENDESK_USER="test_user",
            ZENDESK_API_KEY="test_key"
    )
    @patch('commerce_coordinator.apps.commercetools.utils.logger.debug')
    def test_create_zendesk_ticket_success(self, mock_logger):
        tags = 'test_tags'
        subject = 'test_subject'
        body = 'test_body'

        with requests_mock.Mocker(real_http=True, case_sensitive=False) as mocker:
            mocker.post(
                f"{settings.ZENDESK_URL}/api/v2/tickets.json",
                status_code=201
            )

            create_zendesk_ticket(
                get_edx_lms_user_name(self.user),
                self.user.email,
                subject,
                body,
                tags
            )

            mock_logger.assert_called_once_with('Successfully created ticket.')

    @override_settings(
            ZENDESK_URL="https://test_url",
            ZENDESK_USER="test_user",
            ZENDESK_API_KEY="test_key"
    )
    @patch('commerce_coordinator.apps.commercetools.utils.logger.error')
    def test_create_zendesk_ticket_status_code_fail(self, mock_logger):
        tags = 'test_tags'
        subject = 'test_subject'
        body = 'test_body'

        with requests_mock.Mocker(real_http=True, case_sensitive=False) as mocker:
            mocker.post(
                f"{settings.ZENDESK_URL}/api/v2/tickets.json",
                status_code=400
            )

            create_zendesk_ticket(
                get_edx_lms_user_name(self.user),
                self.user.email,
                subject,
                body,
                tags
            )

            mock_logger.assert_called_once_with('Failed to create ticket. Status: [%d], Body: [%s]', 400, b'')

    @override_settings(
            ZENDESK_URL="https://test_url",
            ZENDESK_USER="test_user",
            ZENDESK_API_KEY="test_key"
    )
    @patch("commerce_coordinator.apps.commercetools.utils.create_zendesk_ticket")
    @patch('commerce_coordinator.apps.commercetools.utils.logger.exception')
    def test_create_zendesk_ticket_failed_response(self, mock_logger, mock_create_zendesk_ticket):
        mock_create_zendesk_ticket.side_effect = Exception("Connection error")
        tags = 'test_tags'
        subject = 'test_subject'
        body = 'test_body'

        with pytest.raises(Exception) as exc:
            create_zendesk_ticket(
                get_edx_lms_user_name(self.user),
                self.user.email,
                subject,
                body,
                tags
            )
            mock_logger.assert_called_once_with(f'Failed to create ticket. Exception: {exc.value}')


class TestRetirementAnonymizingTestCase(unittest.TestCase):
    """
    Tests for anonymizing/hashing incomming field values
    in Create Retired Fields Utils class
    """
    def setUp(self):
        self.field_value = "TestValue"
        self.salt = "TestSalt"
        self.salt_list = ["Salt1", "Salt2", self.salt]
        self.expected_hash = hashlib.sha256((self.salt.encode() + self.field_value.lower().encode('utf-8'))).hexdigest()
        self.expected_retired_field = f"retired_user_{self.expected_hash}"

    def test_create_retired_fields(self):
        result = create_retired_fields(self.field_value, self.salt_list)
        self.assertEqual(result, self.expected_retired_field)

    def test_create_retired_fields_with_invalid_salt_list(self):
        with self.assertRaises(ValueError):
            create_retired_fields(self.field_value, "invalid_salt_list")
