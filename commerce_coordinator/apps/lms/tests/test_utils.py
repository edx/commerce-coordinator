"""
Tests for lms utils
"""
import unittest
from unittest.mock import Mock, patch

import ddt
from django.core.cache import cache
from django.test import RequestFactory, SimpleTestCase, override_settings
from requests.exceptions import RequestException

from commerce_coordinator.apps.core.tests.utils import name_test
from commerce_coordinator.apps.lms.constants import CT_ABSOLUTE_DISCOUNT_TYPE, DEFAULT_BUNDLE_DISCOUNT_KEY
from commerce_coordinator.apps.lms.utils import (
    extract_uuids_from_predicate,
    get_alacarte_checkout_url,
    get_course_uuid,
    get_order_line_item_info_from_entitlement_uuid,
    get_program_offer
)

TEST_COURSE_RUN_KEY = 'course-v1:edX+DemoX+Demo_Course'
TEST_COURSE_UUID = '3bdf1dd1-49be-4a15-9145-38901f578c5a'


class TestGetLineItemFromEntitlement(unittest.TestCase):
    """
    Tests for get_line_item_from_entitlement function
    """

    def get_mock_order_data(self, mock_line_items):
        """
        Create a mock order object with the given line items.
        """
        mock_order = Mock()
        mock_order.id = 'order123'
        mock_order.line_items = mock_line_items
        return mock_order

    def get_mock_line_item_data(self, return_value):
        """
        Create a mock line item object with the given return value for the custom field.
        """
        mock_line_item = Mock()
        mock_line_item.id = 'line_item123'
        mock_line_item.custom.fields.get.return_value = return_value

        return mock_line_item

    @patch('commerce_coordinator.apps.lms.utils.CommercetoolsAPIClient')
    def test_get_line_item_from_entitlement_success(self, MockCommercetoolsAPIClient):
        mock_ct_api_client = MockCommercetoolsAPIClient.return_value
        mock_line_item = self.get_mock_line_item_data('entitlement123')
        mock_order = self.get_mock_order_data([mock_line_item])
        mock_ct_api_client.get_order_by_number.return_value = mock_order

        order_id, line_item_id = get_order_line_item_info_from_entitlement_uuid('order123', 'entitlement123')

        self.assertEqual(order_id, 'order123')
        self.assertEqual(line_item_id, 'line_item123')

    @patch('commerce_coordinator.apps.lms.utils.CommercetoolsAPIClient')
    def test_get_line_item_from_entitlement_no_matching_entitlement(self, MockCommercetoolsAPIClient):
        mock_ct_api_client = MockCommercetoolsAPIClient.return_value
        mock_line_item = self.get_mock_line_item_data('different_entitlement')
        mock_order = self.get_mock_order_data([mock_line_item])
        mock_ct_api_client.get_order_by_number.return_value = mock_order

        order_id, line_item_id = get_order_line_item_info_from_entitlement_uuid('order123', 'entitlement123')

        self.assertEqual(order_id, 'order123')
        self.assertEqual(line_item_id, '')

    @patch('commerce_coordinator.apps.lms.utils.CommercetoolsAPIClient')
    def test_get_line_item_from_entitlement_no_line_items(self, MockCommercetoolsAPIClient):
        mock_ct_api_client = MockCommercetoolsAPIClient.return_value
        mock_order = self.get_mock_order_data([])
        mock_ct_api_client.get_order_by_number.return_value = mock_order

        order_id, line_item_id = get_order_line_item_info_from_entitlement_uuid('order123', 'entitlement123')

        self.assertEqual(order_id, 'order123')
        self.assertEqual(line_item_id, '')


class TestGetProgramOffer(unittest.TestCase):
    """
    Tests for get_program_offer util function
    """
    def setUp(self):
        self.cart_discounts = [
            {
                "key": "BUNDLE_15_OFF",
                "cartPredicate": 'custom.bundleId is defined and (custom.bundleId = "bundle-key-123")',
                "value": {"type": "absolute", "money": [{"centAmount": 1500}]}
            },
            {
                "key": DEFAULT_BUNDLE_DISCOUNT_KEY,
                "cartPredicate": 'custom.bundleId is defined and (custom.bundleId != "bundle-key-123")',
                "value": {"type": "relative", "permyriad": 1000}
            }
        ]

    def test_extract_uuids_from_predicate(self):
        predicate = 'custom.bundleId = "12345" and custom.bundleId = "67890"'
        result = extract_uuids_from_predicate(predicate)
        self.assertEqual(result, ["12345", "67890"])

    def test_get_program_offer_with_specific_bundle(self):
        bundle_key = "bundle-key-123"
        expected_result = {
            "discount_value_in_cents": 1500,
            "discount_type": "absolute",
            "key": "BUNDLE_15_OFF"
        }
        self.assertEqual(get_program_offer(self.cart_discounts, bundle_key), expected_result)

    def test_get_program_offer_with_default_discount(self):
        bundle_key = "non-existent-bundle"
        expected_result = {
            "discount_value_in_cents": 1000,
            "discount_type": "relative",
            "key": DEFAULT_BUNDLE_DISCOUNT_KEY
        }
        self.assertEqual(get_program_offer(self.cart_discounts, bundle_key), expected_result)

    def test_get_program_offer_with_no_matching_discount(self):
        bundle_key = "unknown-bundle"
        self.assertIsNone(get_program_offer([], bundle_key))

    def test_get_program_offer_excluded_from_default_discount(self):
        cart_discounts = [
            {
                "key": DEFAULT_BUNDLE_DISCOUNT_KEY,
                "cartPredicate": 'custom.bundleId != "bundle_3"',
                "value": {"type": CT_ABSOLUTE_DISCOUNT_TYPE, "money": [{"centAmount": 1000}]}
            }
        ]
        bundle_key = "bundle_3"
        result = get_program_offer(cart_discounts, bundle_key)
        self.assertIsNone(result)


class TestGetCourseUuid(SimpleTestCase):
    """
    Tests for get_course_uuid function
    """

    def setUp(self):
        super().setUp()
        cache.clear()

    @patch('commerce_coordinator.apps.lms.utils.DiscoveryAPIClient')
    def test_returns_the_uuid_and_keeps_it(self, client_mock):
        """ The UUID comes from Discovery once, and then from the cache."""
        client_mock.return_value.get_course_uuid.return_value = TEST_COURSE_UUID

        self.assertEqual(get_course_uuid(TEST_COURSE_RUN_KEY), TEST_COURSE_UUID)
        self.assertEqual(get_course_uuid(TEST_COURSE_RUN_KEY), TEST_COURSE_UUID)

        client_mock.return_value.get_course_uuid.assert_called_once_with(TEST_COURSE_RUN_KEY)

    @patch('commerce_coordinator.apps.lms.utils.DiscoveryAPIClient')
    def test_returns_none_and_keeps_nothing_when_discovery_fails(self, client_mock):
        """ An error of Discovery gives None, and the next call asks Discovery again."""
        client_mock.return_value.get_course_uuid.side_effect = [RequestException, TEST_COURSE_UUID]

        self.assertIsNone(get_course_uuid(TEST_COURSE_RUN_KEY))
        self.assertEqual(get_course_uuid(TEST_COURSE_RUN_KEY), TEST_COURSE_UUID)

    @patch('commerce_coordinator.apps.lms.utils.DiscoveryAPIClient')
    def test_returns_none_when_the_course_run_has_no_uuid(self, client_mock):
        """ A course run without a course UUID gives None, and None is not kept."""
        client_mock.return_value.get_course_uuid.return_value = None

        self.assertIsNone(get_course_uuid(TEST_COURSE_RUN_KEY))
        self.assertIsNone(cache.get(f'alacarte.course_uuid.{TEST_COURSE_RUN_KEY}'))


@ddt.ddt
@override_settings(ALACARTE_CHECKOUT_URL='https://learner-home.example.com/aca-checkout')
class TestGetAlacarteCheckoutUrl(SimpleTestCase):
    """
    Tests for get_alacarte_checkout_url function
    """

    def setUp(self):
        super().setUp()
        flag_patch = patch('commerce_coordinator.apps.lms.utils.is_redirect_to_alacarte_enabled_for_user')
        self.flag_mock = flag_patch.start()
        self.flag_mock.return_value = True
        self.addCleanup(flag_patch.stop)

        uuid_patch = patch('commerce_coordinator.apps.lms.utils.get_course_uuid')
        self.course_uuid_mock = uuid_patch.start()
        self.course_uuid_mock.return_value = TEST_COURSE_UUID
        self.addCleanup(uuid_patch.stop)

    @staticmethod
    def get_request(query_params):
        """ Build a payment page redirect request with the given query params."""
        return RequestFactory().get('/lms/payment_page_redirect/', query_params)

    def test_course_purchase_goes_to_alacarte(self):
        """ The a la carte URL has the course UUID and the course run key, and nothing else of the link."""
        request = self.get_request({'sku': ['ABC123'], 'course_run_key': TEST_COURSE_RUN_KEY, 'code': 'DISCOUNT'})

        self.assertEqual(
            get_alacarte_checkout_url(request),
            f'https://learner-home.example.com/aca-checkout?course_uuid={TEST_COURSE_UUID}'
            '&course_run_key=course-v1%3AedX%2BDemoX%2BDemo_Course'
        )
        self.course_uuid_mock.assert_called_once_with(TEST_COURSE_RUN_KEY)

    def test_flag_off_keeps_the_checkout_and_asks_nothing(self):
        """ Without the flag, there is no URL and Discovery is not asked."""
        self.flag_mock.return_value = False

        self.assertIsNone(get_alacarte_checkout_url(self.get_request({'course_run_key': TEST_COURSE_RUN_KEY})))
        self.course_uuid_mock.assert_not_called()

    @ddt.data(
        name_test("test no course run key", {'sku': ['ABC123']}),
        name_test("test two course run keys", {'course_run_key': [TEST_COURSE_RUN_KEY, 'course-v1:edX+Other+Run']}),
        name_test("test program", {'sku': ['A', 'B'], 'bundle': '818aff6f-1a39-4515-8779-dfebc0742d8e'}),
        name_test("test enterprise catalog", {'course_run_key': TEST_COURSE_RUN_KEY, 'catalog': 'abc'}),
        name_test("test credit variant sku", {'course_run_key': f'credit-{TEST_COURSE_RUN_KEY}'}),
        name_test("test not a course run key", {'course_run_key': 'meow'}),
        name_test("test blank course run key", {'course_run_key': ' '}),
    )
    def test_other_purchases_keep_the_checkout_and_ask_nothing(self, query_params):
        """ Only a link with one course run key goes to a la carte."""
        self.assertIsNone(get_alacarte_checkout_url(self.get_request(query_params)))
        self.course_uuid_mock.assert_not_called()

    def test_course_without_a_uuid_keeps_the_checkout(self):
        """ When Discovery gives no course UUID, there is no URL."""
        self.course_uuid_mock.return_value = None

        self.assertIsNone(get_alacarte_checkout_url(self.get_request({'course_run_key': TEST_COURSE_RUN_KEY})))
