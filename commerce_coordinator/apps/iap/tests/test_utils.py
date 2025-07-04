"""
Tests for utility functions in the InAppPurchase app.
"""

from decimal import Decimal
from unittest import TestCase, mock

from commercetools.platform.models import Customer
from rest_framework import status

from commerce_coordinator.apps.commercetools.catalog_info.constants import EdXFieldNames
from commerce_coordinator.apps.iap.payment_processor import (
    PaymentError,
    RedundantPaymentError,
    UserCancelled,
    ValidationError
)
from commerce_coordinator.apps.iap.utils import (
    _get_attributes_to_update,
    convert_localized_price_to_ct_cent_amount,
    get_ct_customer,
    get_email_domain,
    get_payment_info_from_purchase_token,
    get_standalone_price_for_sku
)


class GetEmailDomainTests(TestCase):
    """Tests for get_email_domain function."""

    def test_get_email_domain_with_valid_email(self):
        """Test extraction of domain from a valid email address."""
        email = "test@example.com"
        self.assertEqual(get_email_domain(email), "example.com")

    def test_get_email_domain_with_uppercase_email(self):
        """Test that the function converts email to lowercase."""
        email = "Test@Example.Com"
        self.assertEqual(get_email_domain(email), "example.com")

    def test_get_email_domain_with_spaces(self):
        """Test that the function handles whitespace."""
        email = "  test@example.com  "
        self.assertEqual(get_email_domain(email), "example.com")

    def test_get_email_domain_with_empty_string(self):
        """Test handling of empty email."""
        self.assertEqual(get_email_domain(""), "")

    def test_get_email_domain_with_none(self):
        """Test handling of None email."""
        self.assertEqual(get_email_domain(None), "")

    def test_get_email_domain_without_at_symbol(self):
        """Test handling of invalid email without @ symbol."""
        email = "testexample.com"
        self.assertEqual(get_email_domain(email), "")


class GetAttributesToUpdateTests(TestCase):
    """Tests for _get_attributes_to_update function."""

    def setUp(self):
        """Set up common test data."""
        self.customer = mock.MagicMock(spec=Customer)
        self.customer.email = "existing@example.com"
        self.customer.first_name = "Existing"
        self.customer.last_name = "User"

        self.customer.custom = mock.MagicMock()
        self.customer.custom.fields = {
            EdXFieldNames.LMS_USER_NAME: "existing_username"
        }

        self.user = mock.MagicMock()
        self.user.username = "new_username"
        self.user.email = "new@example.com"

    def test_all_fields_different(self):
        """Test when all fields need to be updated."""
        updates = _get_attributes_to_update(
            user=self.user,
            customer=self.customer,
            first_name="New",
            last_name="Name",
        )

        expected = {
            "lms_username": "new_username",
            "email": "new@example.com",
            "first_name": "New",
            "last_name": "Name",
        }
        self.assertEqual(updates, expected)

    def test_no_fields_different(self):
        """Test when no fields need to be updated."""
        self.user.username = "existing_username"
        self.user.email = "existing@example.com"

        updates = _get_attributes_to_update(
            user=self.user,
            customer=self.customer,
            first_name="Existing",
            last_name="User",
        )

        self.assertEqual(updates, {})

    def test_some_fields_different(self):
        """Test when only some fields need to be updated."""
        self.user.username = "existing_username"

        updates = _get_attributes_to_update(
            user=self.user,
            customer=self.customer,
            first_name="New",
            last_name="User",
        )

        expected = {
            "email": "new@example.com",
            "first_name": "New",
        }
        self.assertEqual(updates, expected)

    def test_customer_without_custom_fields(self):
        """Test when customer has no custom fields."""
        self.customer.custom = None

        updates = _get_attributes_to_update(
            user=self.user,
            customer=self.customer,
            first_name="New",
            last_name="Name",
        )

        expected = {
            "lms_username": "new_username",
            "email": "new@example.com",
            "first_name": "New",
            "last_name": "Name",
        }
        self.assertEqual(updates, expected)


class GetCTCustomerTests(TestCase):
    """Tests for get_ct_customer function."""

    def setUp(self):
        """Set up common test data."""
        self.client = mock.MagicMock()
        self.user = mock.MagicMock()
        self.user.lms_user_id = "user123"
        self.user.username = "testuser"
        self.user.email = "test@example.com"
        self.user.first_name = "Test"
        self.user.last_name = "User"
        self.user.full_name = "Test User"

    def test_get_existing_customer_no_updates(self):
        """Test retrieving an existing customer with no updates needed."""
        mock_customer = mock.MagicMock(spec=Customer)
        mock_customer.email = self.user.email
        mock_customer.first_name = self.user.first_name
        mock_customer.last_name = self.user.last_name

        mock_customer.custom = mock.MagicMock()
        mock_customer.custom.fields = {
            EdXFieldNames.LMS_USER_NAME: self.user.username
        }

        self.client.get_customer_by_lms_user_id.return_value = mock_customer

        customer = get_ct_customer(self.client, self.user)

        self.client.get_customer_by_lms_user_id.assert_called_once_with(
            self.user.lms_user_id
        )
        self.client.update_customer.assert_not_called()
        self.assertEqual(customer, mock_customer)

    def test_get_existing_customer_with_updates(self):
        """Test retrieving and updating an existing customer."""
        mock_customer = mock.MagicMock(spec=Customer)
        mock_customer.email = "old@example.com"
        mock_customer.first_name = "Old"
        mock_customer.last_name = "Name"

        mock_customer.custom = mock.MagicMock()
        mock_customer.custom.fields = {EdXFieldNames.LMS_USER_NAME: "oldusername"}

        updated_customer = mock.MagicMock(spec=Customer)
        updated_customer.email = self.user.email
        updated_customer.first_name = self.user.first_name
        updated_customer.last_name = self.user.last_name
        updated_customer.custom = mock.MagicMock()
        updated_customer.custom.fields = {
            EdXFieldNames.LMS_USER_NAME: self.user.username
        }

        self.client.get_customer_by_lms_user_id.return_value = mock_customer
        self.client.update_customer.return_value = updated_customer

        customer = get_ct_customer(self.client, self.user)

        self.client.get_customer_by_lms_user_id.assert_called_once_with(
            self.user.lms_user_id
        )
        self.client.update_customer.assert_called_once()
        self.assertEqual(customer, updated_customer)

    def test_create_new_customer(self):
        """Test creating a new customer when none exists."""
        self.client.get_customer_by_lms_user_id.return_value = None
        mock_new_customer = mock.MagicMock(spec=Customer)
        self.client.create_customer.return_value = mock_new_customer

        customer = get_ct_customer(self.client, self.user)

        self.client.get_customer_by_lms_user_id.assert_called_once_with(
            self.user.lms_user_id
        )
        self.client.create_customer.assert_called_once_with(
            email=self.user.email,
            first_name=self.user.first_name,
            last_name=self.user.last_name,
            lms_user_id=self.user.lms_user_id,
            lms_username=self.user.username,
        )
        self.assertEqual(customer, mock_new_customer)

    def test_create_customer_with_full_name_only(self):
        """Test creating a customer when only full_name is available."""
        self.client.get_customer_by_lms_user_id.return_value = None
        self.user.first_name = ""
        self.user.last_name = ""

        mock_new_customer = mock.MagicMock(spec=Customer)
        self.client.create_customer.return_value = mock_new_customer

        customer = get_ct_customer(self.client, self.user)

        self.client.create_customer.assert_called_once_with(
            email=self.user.email,
            first_name="Test",
            last_name="User",
            lms_user_id=self.user.lms_user_id,
            lms_username=self.user.username,
        )

        self.assertEqual(customer, mock_new_customer)


class GetStandalonePriceForSkuTests(TestCase):
    """Tests for get_standalone_price_for_sku function."""

    def setUp(self):
        """Set up test environment with mocked API client."""
        self.patcher = mock.patch(
            "commerce_coordinator.apps.iap.utils.CTCustomAPIClient"
        )
        self.mock_client_class = self.patcher.start()
        self.mock_client = self.mock_client_class.return_value
        self.addCleanup(self.patcher.stop)

    def test_get_valid_price(self):
        """Test retrieving a valid price for a SKU."""
        self.mock_client.get_standalone_prices_for_skus.return_value = [
            {
                "value": {
                    "centAmount": 4999,
                    "currencyCode": "USD",
                    "fractionDigits": 2
                }
            }
        ]

        result = get_standalone_price_for_sku("test-sku")

        self.mock_client.get_standalone_prices_for_skus.assert_called_once_with(
            ["test-sku"]
        )
        self.assertEqual(result.cent_amount, 4999)
        self.assertEqual(result.currency_code, "USD")

    def test_empty_response(self):
        """Test handling of empty response."""
        self.mock_client.get_standalone_prices_for_skus.return_value = []

        with self.assertRaises(ValueError) as context:
            get_standalone_price_for_sku("test-sku")

        self.assertIn("No standalone price found", str(context.exception))

    def test_malformed_response(self):
        """Test handling of malformed response."""
        self.mock_client.get_standalone_prices_for_skus.return_value = [
            {"wrong_key": "data"}
        ]

        with self.assertRaises(ValueError) as context:
            get_standalone_price_for_sku("test-sku")

        self.assertIn("No standalone price found", str(context.exception))


class GetPaymentProcessorTests(TestCase):
    """Tests for get_payment_info_from_purchase_token function."""

    def setUp(self):
        self.request_data = {
            "payment_processor": "android_iap",
            "purchase_token": "test-token"
        }
        self.cart = mock.MagicMock()
        self.price = Decimal("9.99")  # Add a sample price to pass in tests

    @mock.patch("commerce_coordinator.apps.iap.utils.IAPPaymentProcessor")
    def test_valid_android_iap(self, MockProcessor):
        """Test valid Android IAP payment processor."""
        mock_processor_instance = MockProcessor.return_value
        mock_processor_instance.validate_iap.return_value = {"success": True}

        result = get_payment_info_from_purchase_token(self.request_data, self.cart, self.price)

        self.assertEqual(result["status_code"], status.HTTP_200_OK)
        self.assertEqual(result["response"], {"success": True})
        mock_processor_instance.validate_iap.assert_called_once_with(self.request_data, self.cart, self.price)

    @mock.patch("commerce_coordinator.apps.iap.utils.IAPPaymentProcessor")
    def test_validation_error(self, MockProcessor):
        """Test ValidationError handling."""
        MockProcessor.return_value.validate_iap.side_effect = ValidationError("Invalid token")

        result = get_payment_info_from_purchase_token(self.request_data, self.cart, self.price)
        self.assertEqual(result["status_code"], status.HTTP_400_BAD_REQUEST)
        self.assertEqual(result["response"], {"error": "Invalid token"})

    @mock.patch("commerce_coordinator.apps.iap.utils.IAPPaymentProcessor")
    def test_redundant_payment_error(self, MockProcessor):
        """Test RedundantPaymentError handling."""
        MockProcessor.return_value.validate_iap.side_effect = RedundantPaymentError("Duplicate payment")

        result = get_payment_info_from_purchase_token(self.request_data, self.cart, self.price)
        self.assertEqual(result["status_code"], status.HTTP_409_CONFLICT)
        self.assertEqual(result["response"], {"error": "Duplicate payment"})

    @mock.patch("commerce_coordinator.apps.iap.utils.IAPPaymentProcessor")
    def test_user_cancelled_error(self, MockProcessor):
        """Test UserCancelled exception handling."""
        MockProcessor.return_value.validate_iap.side_effect = UserCancelled("User cancelled payment")

        result = get_payment_info_from_purchase_token(self.request_data, self.cart, self.price)
        self.assertEqual(result["status_code"], status.HTTP_400_BAD_REQUEST)
        self.assertEqual(result["response"], {"error": "User cancelled payment"})

    @mock.patch("commerce_coordinator.apps.iap.utils.IAPPaymentProcessor")
    def test_payment_error(self, MockProcessor):
        """Test PaymentError handling."""
        MockProcessor.return_value.validate_iap.side_effect = PaymentError("Payment expired")

        result = get_payment_info_from_purchase_token(self.request_data, self.cart, self.price)
        self.assertEqual(result["status_code"], status.HTTP_400_BAD_REQUEST)
        self.assertEqual(result["response"], {"error": "Payment expired"})

    @mock.patch("commerce_coordinator.apps.iap.utils.IAPPaymentProcessor")
    def test_unexpected_exception(self, MockProcessor):
        """Test unexpected exception handling."""
        MockProcessor.return_value.validate_iap.side_effect = Exception("Unexpected error")

        result = get_payment_info_from_purchase_token(self.request_data, self.cart, self.price)
        self.assertEqual(result["status_code"], status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(result["response"], {"error": "Internal Server Error"})

    def test_unsupported_processor(self):
        """Test unsupported payment processor."""
        self.request_data["payment_processor"] = "unsupported-processor"

        result = get_payment_info_from_purchase_token(self.request_data, self.cart, self.price)
        self.assertEqual(result["status_code"], status.HTTP_400_BAD_REQUEST)
        self.assertEqual(result["response"], {"error": "Unsupported payment processor"})


class ConvertLocalizedPriceToCTCentAmountTests(TestCase):
    """Tests for convert_localized_price_to_ct_cent_amount function."""

    def test_convert_localized_price_with_default_exponent(self):
        """Test converting decimal price with default exponent."""
        result = convert_localized_price_to_ct_cent_amount(
            amount=Decimal("1.01"), currency_code="PKR"
        )
        self.assertEqual(result, 101)

    def test_convert_ios_price(self):
        """Test converting an iOS price to cents."""
        result = convert_localized_price_to_ct_cent_amount(
            amount=1010, currency_code="USD", exponent=3
        )
        self.assertEqual(result, 101)

    def test_convert_with_non_standard_currency(self):
        """Test converting with a currency that has 0 fraction digits"""
        result = convert_localized_price_to_ct_cent_amount(
            amount=Decimal("100.01"), currency_code="JPY"
        )
        self.assertEqual(result, 100)
