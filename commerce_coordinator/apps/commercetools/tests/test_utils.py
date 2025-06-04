"""
Tests for Commerce tools utils
"""
import hashlib
import re
import unittest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, Mock, patch

from braze.client import BrazeClient
from commercetools.platform.models import (
    CentPrecisionMoney,
    MoneyType,
    ReturnPaymentState,
    TransactionState,
    TransactionType,
    TypedMoney
)
from django.conf import settings
from django.test import override_settings
from django.urls import reverse

from commerce_coordinator.apps.commercetools.tests.conftest import (
    gen_order,
    gen_payment,
    gen_payment_with_multiple_transactions
)
from commerce_coordinator.apps.commercetools.tests.constants import EXAMPLE_FULFILLMENT_SIGNAL_PAYLOAD
from commerce_coordinator.apps.commercetools.utils import (
    calculate_total_discount_on_order,
    convert_ct_cent_amount_to_localized_price,
    create_retired_fields,
    extract_ct_order_information_for_braze_canvas,
    extract_ct_product_information_for_braze_canvas,
    find_latest_refund,
    find_refund_transaction,
    format_amount_for_braze_canvas,
    format_iso_like_currency_spacing,
    get_braze_client,
    get_refund_transaction_id_from_order,
    get_unprocessed_return_item_ids_from_order,
    has_full_refund_transaction,
    has_refund_transaction,
    prepare_default_params,
    send_fulfillment_error_email,
    send_order_confirmation_email,
    translate_refund_status_to_transaction_status
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

    @override_settings(
        BRAZE_API_KEY="braze_api_key",
        BRAZE_API_SERVER="braze_api_server",
        BRAZE_CT_FULFILLMENT_UNSUPPORTED_MODE_ERROR_CANVAS_ID="dummy_canvas"
    )
    @patch('commerce_coordinator.apps.commercetools.utils.get_braze_client')
    def test_send_fulfillment_error_email_success(self, mock_get_braze_client):
        mock_braze_client = Mock()
        mock_get_braze_client.return_value = mock_braze_client

        canvas_entry_properties = {}
        lms_user_id = 'user123'
        lms_user_email = 'user@example.com'

        with patch.object(mock_braze_client, 'send_canvas_message') as mock_send_canvas_message:
            send_fulfillment_error_email(
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
        BRAZE_CT_FULFILLMENT_UNSUPPORTED_MODE_ERROR_CANVAS_ID="dummy_canvas"
    )
    @patch('commerce_coordinator.apps.commercetools.utils.get_braze_client')
    @patch('commerce_coordinator.apps.commercetools.utils.logger.exception')
    def test_send_fulfillment_error_email_failure(self, mock_logger, mock_get_braze_client):
        mock_braze_client = Mock()
        mock_get_braze_client.return_value = mock_braze_client

        canvas_entry_properties = {}
        lms_user_id = 'user123'
        lms_user_email = 'user@example.com'

        with patch.object(mock_braze_client, 'send_canvas_message') as mock_send_canvas_message:
            mock_send_canvas_message.side_effect = Exception('Error sending Braze email')
            send_fulfillment_error_email(
                lms_user_id, lms_user_email, canvas_entry_properties
            )

            mock_send_canvas_message.assert_called_once_with(
                canvas_id='dummy_canvas',
                recipients=[{"external_user_id": lms_user_id, "attributes": {"email": lms_user_email}}],
                canvas_entry_properties=canvas_entry_properties,
            )
            mock_logger.assert_called_once_with('Encountered exception sending Fulfillment error '
                                                'email. Exception: Error sending Braze email')

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


class TestCalculateDiscount(unittest.TestCase):
    """Test for calculate_total_discount_on_order function"""

    def test_calculate_total_discount_on_order(self):
        order = gen_order(EXAMPLE_FULFILLMENT_SIGNAL_PAYLOAD['order_number'], with_discount=False)

        # Mock the discount on total price
        discount_on_total_price = CentPrecisionMoney(
            cent_amount=500,
            currency_code='USD',
            fraction_digits=2
        )
        order.discount_on_total_price = MagicMock()
        order.discount_on_total_price.discounted_amount = discount_on_total_price

        # Mock the line items discounts
        discount_on_line_item = CentPrecisionMoney(
            cent_amount=300,
            currency_code='USD',
            fraction_digits=2
        )
        line_item = MagicMock()
        line_item.discounted_price_per_quantity = [
            MagicMock(discounted_price=MagicMock(
                included_discounts=[MagicMock(discounted_amount=discount_on_line_item)]
            ))
        ]
        line_item.price = MagicMock()
        line_item.price.value.cent_amount = 1000
        line_item.price.discounted.value.cent_amount = 700
        order.line_items = [line_item]

        total_discount = calculate_total_discount_on_order(order)

        expected_total_discount = CentPrecisionMoney(
            cent_amount=1100,
            currency_code='USD',
            fraction_digits=2
        )
        self.assertEqual(total_discount.cent_amount, expected_total_discount.cent_amount)
        self.assertEqual(total_discount.currency_code, expected_total_discount.currency_code)
        self.assertEqual(total_discount.fraction_digits, expected_total_discount.fraction_digits)

    def test_calculate_discount_on_order_without_cart_level_discount(self):
        order = gen_order(EXAMPLE_FULFILLMENT_SIGNAL_PAYLOAD['order_number'], with_discount=False)
        order.discount_on_total_price = None

        discount_on_line_item = CentPrecisionMoney(
            cent_amount=300,
            currency_code='USD',
            fraction_digits=2
        )
        line_item = MagicMock()
        line_item.discounted_price_per_quantity = [
            MagicMock(discounted_price=MagicMock(
                included_discounts=[MagicMock(discounted_amount=discount_on_line_item)]
            ))
        ]
        line_item.price = MagicMock()
        line_item.price.value.cent_amount = 1000
        line_item.price.discounted.value.cent_amount = 700
        order.line_items = [line_item]

        total_discount = calculate_total_discount_on_order(order)

        expected_total_discount = CentPrecisionMoney(
            cent_amount=600,
            currency_code='USD',
            fraction_digits=2
        )
        self.assertEqual(total_discount.cent_amount, expected_total_discount.cent_amount)
        self.assertEqual(total_discount.currency_code, expected_total_discount.currency_code)
        self.assertEqual(total_discount.fraction_digits, expected_total_discount.fraction_digits)


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


class TestFindRefundTransaction(unittest.TestCase):
    """
    Tests for Find Refund Transaction Utils function
    """

    def test_has_no_refund_transaction(self):
        payment = gen_payment_with_multiple_transactions(TransactionType.CHARGE, 4900)
        self.assertEqual(find_refund_transaction(payment, 4900), '')

    def test_has_matching_refund_transaction(self):
        payment = gen_payment_with_multiple_transactions(TransactionType.CHARGE, 4900, TransactionType.REFUND,
                                                         TypedMoney(cent_amount=4900,
                                                                    currency_code='USD',
                                                                    type=MoneyType.CENT_PRECISION,
                                                                    fraction_digits=2))
        self.assertEqual(find_refund_transaction(payment, 'ch_3P9RWsH4caH7G0X11toRGUJf'), payment.transactions[1].id)

    def test_has_no_matching_refund_transaction(self):
        payment = gen_payment_with_multiple_transactions(TransactionType.CHARGE, 4900, TransactionType.REFUND,
                                                         TypedMoney(cent_amount=4900,
                                                                    currency_code='USD',
                                                                    type=MoneyType.CENT_PRECISION,
                                                                    fraction_digits=2))
        self.assertEqual(find_refund_transaction(payment, 4000), '')


class TestFindLatestRefund(unittest.TestCase):
    """
    Tests for find_latest_refund function
    """

    def test_has_no_refund_transaction(self):
        payment = gen_payment_with_multiple_transactions(TransactionType.CHARGE, 4900)
        self.assertEqual(find_latest_refund(payment), '')

    def test_has_matching_refund_transaction(self):
        payment = gen_payment_with_multiple_transactions(TransactionType.CHARGE, 4900, TransactionType.REFUND,
                                                         TypedMoney(cent_amount=4900,
                                                                    currency_code='USD',
                                                                    type=MoneyType.CENT_PRECISION,
                                                                    fraction_digits=2))
        self.assertEqual(find_latest_refund(payment), payment.transactions[1].id)


class TestTranslateStripeRefundStatus(unittest.TestCase):
    """
    Tests for Translating Stripes Refund Status Utils class
    """

    def test_translate_stripe_refund_status_succeeded(self):
        self.assertEqual(translate_refund_status_to_transaction_status('succeeded'), TransactionState.SUCCESS)

    def test_translate_stripe_refund_status_pending(self):
        self.assertEqual(translate_refund_status_to_transaction_status('pending'), TransactionState.PENDING)

    def test_translate_stripe_refund_status_failed(self):
        self.assertEqual(translate_refund_status_to_transaction_status('failed'), TransactionState.FAILURE)

    def test_translate_stripe_refund_status_other(self):
        # Test for an unknown status
        self.assertEqual(translate_refund_status_to_transaction_status('unknown_status'), TransactionState.SUCCESS)


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


class TestPrepareDefaultParams(unittest.TestCase):
    """Tests for prepare_default_params function."""

    def test_prepare_default_params(self):
        """Test that default parameters are correctly prepared."""

        mock_order = Mock()
        mock_order.order_number = "ORD-12345"
        mock_order.id = "testorder"
        mock_order.last_modified_at = datetime(2025, 4, 28, 10, 30, 0, tzinfo=timezone.utc)

        params = prepare_default_params(mock_order, "testuser", "commercetools")

        expected_params = {
            'email_opt_in': True,
            'order_number': "ORD-12345",
            'order_id': "testorder",
            'provider_id': None,
            'edx_lms_user_id': "testuser",
            'date_placed': "2025-04-28T10:30:00Z",
            'source_system': "commercetools",
        }

        self.assertEqual(params, expected_params)


class TestGetRefundTransactionIdFromMobileOrder(unittest.TestCase):
    """
    Tests for get_refund_transaction_id_from_mobile_order function
    """

    def test_get_refund_transaction_id_with_refund(self):
        # Mock an order with a refund transaction
        refund_transaction = MagicMock()
        refund_transaction.type = TransactionType.REFUND
        refund_transaction.id = "refund_transaction_id"

        payment = MagicMock()
        payment.transactions = [refund_transaction]

        payment_reference = MagicMock()
        payment_reference.obj = payment

        order = MagicMock()
        order.payment_info = MagicMock()
        order.payment_info.payments = [payment_reference]

        result = get_refund_transaction_id_from_order(order)
        self.assertEqual(result, "refund_transaction_id")

    def test_get_refund_transaction_id_without_refund(self):
        # Mock an order with no refund transactions
        charge_transaction = MagicMock()
        charge_transaction.type = TransactionType.CHARGE

        payment = MagicMock()
        payment.transactions = [charge_transaction]

        payment_reference = MagicMock()
        payment_reference.obj = payment

        order = MagicMock()
        order.payment_info = MagicMock()
        order.payment_info.payments = [payment_reference]

        result = get_refund_transaction_id_from_order(order)
        self.assertEqual(result, "")


class TestExtractReturnItemIds(unittest.TestCase):
    """
    Tests for get_unprocessed_return_item_ids_from_order function
    """

    def test_extract_return_item_ids_with_refunded_items_no_transaction(self):
        return_item = MagicMock()
        return_item.id = "return_item_1"
        return_item.payment_state = ReturnPaymentState.REFUNDED
        return_item.custom = None
        return_item2 = MagicMock()
        return_item2.id = "return_item_2"
        return_item2.payment_state = ReturnPaymentState.REFUNDED
        return_item2.custom = None
        return_info = MagicMock()
        return_info.items = [return_item, return_item2]

        order = MagicMock()
        order.return_info = [return_info]

        result = get_unprocessed_return_item_ids_from_order(order)
        self.assertEqual(result, ["return_item_1", "return_item_2"])

    def test_extract_return_item_ids_with_non_refunded_items(self):
        return_item = MagicMock()
        return_item.id = "return_item_1"
        return_item.payment_state = ReturnPaymentState.NOT_REFUNDED
        return_info = MagicMock()
        return_info.items = [return_item]

        order = MagicMock()
        order.return_info = [return_info]

        result = get_unprocessed_return_item_ids_from_order(order)
        self.assertEqual(result, [])


class TestCurrencyFormattingUtils(unittest.TestCase):
    """
    Unit tests for currency formatting utility functions.
    """

    def test_convert_ct_cent_amount_usd(self):
        result = convert_ct_cent_amount_to_localized_price(cent_amount=1099, fraction_digits=2)
        self.assertEqual(result, Decimal('10.99'))

    def test_convert_ct_cent_amount_jpy(self):
        result = convert_ct_cent_amount_to_localized_price(cent_amount=5000, fraction_digits=0)
        self.assertEqual(result, Decimal('5000'))

    def test_convert_ct_cent_amount_with_zero(self):
        result = convert_ct_cent_amount_to_localized_price(cent_amount=0, fraction_digits=2)
        self.assertEqual(result, Decimal('0.00'))

    def test_format_currency_symbol_differs_from_code(self):
        result = format_iso_like_currency_spacing(Decimal('123.45'), 'USD')
        self.assertIn('$', result)
        self.assertNotIn('USD ', result)

    def test_format_currency_symbol_matches_code(self):
        # For PKR, the symbol is often "PKR", so we expect a space
        result = format_iso_like_currency_spacing(Decimal('2840.00'), 'PKR')
        self.assertTrue(re.match(r'^PKR\s\d', result))  # e.g., 'PKR 2,840.00'

    @patch('commerce_coordinator.apps.commercetools.utils.get_currency_symbol')
    @patch('commerce_coordinator.apps.commercetools.utils.format_currency')
    def test_format_currency_mocked_spacing(self, mock_format_currency, mock_get_currency_symbol):
        mock_format_currency.return_value = 'PKR2840.00'
        mock_get_currency_symbol.return_value = 'PKR'

        result = format_iso_like_currency_spacing(Decimal('2840.00'), 'PKR')
        self.assertEqual(result, 'PKR 2840.00')

    def test_format_amount_for_braze_canvas_usd(self):
        result = format_amount_for_braze_canvas(cent_amount=1099, currency_code='USD', fraction_digits=2)
        self.assertIn('$', result)

    def test_format_amount_for_braze_canvas_iso_code(self):
        result = format_amount_for_braze_canvas(cent_amount=284000, currency_code='PKR', fraction_digits=2)
        self.assertIn('PKR ', result)

    @patch('commerce_coordinator.apps.commercetools.utils.convert_ct_cent_amount_to_localized_price')
    @patch('commerce_coordinator.apps.commercetools.utils.format_iso_like_currency_spacing')
    def test_format_amount_calls_helpers(self, mock_format, mock_convert):
        mock_convert.return_value = Decimal('10.99')
        mock_format.return_value = '$10.99'

        result = format_amount_for_braze_canvas(cent_amount=1099, currency_code='USD', fraction_digits=2)

        mock_convert.assert_called_once_with(1099, 2)
        mock_format.assert_called_once_with(Decimal('10.99'), 'USD')
        self.assertEqual(result, '$10.99')

    @patch('builtins.print')
    @patch('commerce_coordinator.apps.commercetools.utils.convert_ct_cent_amount_to_localized_price')
    def test_format_amount_error_handling(self, mock_convert, mock_print):
        mock_convert.side_effect = ValueError("Invalid currency")

        result = format_amount_for_braze_canvas(cent_amount=1099, currency_code='XYZ', fraction_digits=2)

        mock_print.assert_called_once()
        self.assertIn("XYZ", result)
        self.assertTrue(result.startswith("XYZ "))
        self.assertEqual(result, "XYZ 10.99")
