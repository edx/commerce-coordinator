"""
Tests for utility functions in the InAppPurchase app.
"""

from unittest import TestCase, mock
from unittest.mock import patch, Mock

from commercetools.platform.models import Customer, CentPrecisionMoney, Attribute

from commerce_coordinator.apps.commercetools.catalog_info.constants import EdXFieldNames
from commerce_coordinator.apps.iap.utils import (
    _get_attributes_to_update,
    get_ct_customer,
    get_email_domain,
    get_standalone_price_for_sku,
    sum_money,
    cents_to_dollars,
    get_attribute_value,
    get_product_from_line_item
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


class TestSumMoney(TestCase):
    """Tests for sum_money utility function"""

    def test_sum_money_with_valid_money_objects(self):
        """Test summing multiple valid CentPrecisionMoney objects"""

        money1 = CentPrecisionMoney(cent_amount=1000, currency_code="USD", fraction_digits=2)
        money2 = CentPrecisionMoney(cent_amount=2500, currency_code="USD", fraction_digits=2)
        money3 = CentPrecisionMoney(cent_amount=7500, currency_code="USD", fraction_digits=2)

        result = sum_money(money1, money2, money3)

        assert result['cent_amount'] == 11000
        assert result['currency_code'] == "USD"
        assert result['fraction_digits'] == 2

    def test_sum_money_with_none_values(self):
        """Test summing with None values and edge cases"""

        money1 = CentPrecisionMoney(cent_amount=1000, currency_code="USD", fraction_digits=2)
        money2 = None

        result = sum_money(money1, money2)
        assert result['cent_amount'] == 1000
        assert result['currency_code'] == "USD"
        assert result['fraction_digits'] == 2

        result = sum_money(None, None)
        assert result is None

        result = sum_money()
        assert result is None


class TestCentsToDollars(TestCase):
    """Tests for cents_to_dollars utility function"""

    def test_cents_to_dollars_conversion(self):
        """Test converting cent amount to dollars with various amounts and fraction digits"""

        money1 = CentPrecisionMoney(cent_amount=1000, currency_code="USD", fraction_digits=2)
        result1 = cents_to_dollars(money1)
        assert result1 == 10.00

        money2 = CentPrecisionMoney(cent_amount=12345, currency_code="USD", fraction_digits=3)
        result2 = cents_to_dollars(money2)
        assert result2 == 12.345

        money3 = CentPrecisionMoney(cent_amount=999999, currency_code="USD", fraction_digits=2)
        result3 = cents_to_dollars(money3)
        assert result3 == 9999.99

        money4 = CentPrecisionMoney(cent_amount=1, currency_code="USD", fraction_digits=2)
        result4 = cents_to_dollars(money4)
        assert result4 == 0.01

    def test_cents_to_dollars_edge_cases(self):
        """Test edge cases for cents_to_dollars function"""

        result1 = cents_to_dollars(None)
        assert result1 is None

        money2 = CentPrecisionMoney(cent_amount=0, currency_code="USD", fraction_digits=2)
        result2 = cents_to_dollars(money2)
        assert result2 == 0.0

        money3 = CentPrecisionMoney(cent_amount=None, currency_code="USD", fraction_digits=2)
        result3 = cents_to_dollars(money3)
        assert result3 == 0.0

        money4 = CentPrecisionMoney(cent_amount=1234, currency_code="USD", fraction_digits=None)
        result4 = cents_to_dollars(money4)
        assert result4 == 12.34


class TestGetAttributeValue(TestCase):
    """Tests for get_attribute_value utility function"""

    def test_get_attribute_value_found(self):
        """Test retrieving attribute values that exist in the list"""
        
        # Create test attributes
        attributes = [
            Attribute(name="color", value="red"),
            Attribute(name="size", value="medium"),
            Attribute(name="price", value=19.99),
            Attribute(name="in_stock", value=True)
        ]
        
        # Test string values
        result1 = get_attribute_value(attributes, "color")
        assert result1 == "red"
        
        result2 = get_attribute_value(attributes, "size")
        assert result2 == "medium"
        
        # Test numeric value
        result3 = get_attribute_value(attributes, "price")
        assert result3 == 19.99
        
        # Test boolean value
        result4 = get_attribute_value(attributes, "in_stock")
        assert result4 is True

    def test_get_attribute_value_edge_cases(self):
        """Test edge cases for get_attribute_value function"""
        
        # Create test attributes
        attributes = [
            Attribute(name="empty", value=""),
            Attribute(name="zero", value=0),
            Attribute(name="none_value", value=None)
        ]
        
        # Test with non-existent key
        result1 = get_attribute_value(attributes, "non_existent")
        assert result1 is None
        
        # Test with empty string value
        result2 = get_attribute_value(attributes, "empty")
        assert result2 == ""
        
        # Test with zero value
        result3 = get_attribute_value(attributes, "zero")
        assert result3 == 0
        
        # Test with None value
        result4 = get_attribute_value(attributes, "none_value")
        assert result4 is None
        
        # Test with empty attributes list
        result5 = get_attribute_value([], "any_key")
        assert result5 is None
