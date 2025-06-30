"""
Commercetools app Task Tests
"""

import logging
from unittest.mock import Mock, call, patch

import stripe
from commercetools import CommercetoolsError
from commercetools.platform.models import Money, TransactionType
from django.test import TestCase

from commerce_coordinator.apps.commercetools.tasks import (
    fulfillment_completed_update_ct_line_item_task,
    refund_from_mobile_task,
    refund_from_paypal_task,
    refund_from_stripe_task,
    revoke_line_mobile_order_task
)
from commerce_coordinator.apps.commercetools.tests.conftest import (
    gen_order,
    gen_payment,
    gen_payment_with_multiple_transactions
)
from commerce_coordinator.apps.commercetools.tests.constants import (
    EXAMPLE_RETURNED_ORDER_STRIPE_CLIENT_PAYLOAD,
    EXAMPLE_RETURNED_ORDER_STRIPE_SIGNAL_PAYLOAD,
    EXAMPLE_UPDATE_LINE_ITEM_SIGNAL_PAYLOAD
)
from commerce_coordinator.apps.core.models import User

# Log using module name.
logger = logging.getLogger(__name__)

# Define unit under test.
# Note: if the UUT is part of the class as an ivar, it trims off arg0 as 'self' and
#       claims too many args supplied
fulfillment_uut = fulfillment_completed_update_ct_line_item_task
returned_uut = refund_from_stripe_task
paypal_uut = refund_from_paypal_task
mobile_uut = refund_from_mobile_task


@patch('commerce_coordinator.apps.commercetools.tasks.CommercetoolsAPIClient')
class UpdateLineItemStateOnFulfillmentCompletionTaskTest(TestCase):
    """ Update Line Item State on Fulfillment Completion Task Test """

    @staticmethod
    def unpack_for_uut(values):
        """ Unpack the dictionary in the order required for the UUT """
        return (
            values['entitlement_uuid'],
            values['order_id'],
            values['line_item_id'],
            values['to_state_key']
        )

    def setUp(self):
        User.objects.create(username='test-user', lms_user_id=4)

    def test_correct_arguments_passed(self, mock_client):
        '''
        Check calling uut with mock_parameters yields call to client with
        expected_data.
        '''
        # pylint: disable=no-value-for-parameter
        mock_order = gen_order(EXAMPLE_UPDATE_LINE_ITEM_SIGNAL_PAYLOAD['order_id'])
        mock_client().get_order_by_id.return_value = mock_order
        mock_client().get_state_by_key.return_value = mock_order.line_items[0].state[0].state

        _ = fulfillment_uut(*self.unpack_for_uut(EXAMPLE_UPDATE_LINE_ITEM_SIGNAL_PAYLOAD))
        logger.info('mock_client().mock_calls: %s', mock_client().mock_calls)
        mock_client().update_line_item_on_fulfillment.assert_called_once_with(
            *EXAMPLE_UPDATE_LINE_ITEM_SIGNAL_PAYLOAD.values())


@patch('commerce_coordinator.apps.commercetools.tasks.CommercetoolsAPIClient')
class ReturnedOrderfromStripeTaskTest(TestCase):
    """ Returned Order From Stripe Task Test """

    @staticmethod
    def unpack_for_uut(values):
        """ Unpack the dictionary in the order required for the UUT """
        return (
            values['payment_intent_id'],
            values['stripe_refund'],
        )

    def setUp(self):
        User.objects.create(username='test-user', lms_user_id=4)

    def test_correct_arguments_passed(self, mock_client):
        '''
        Check calling uut with mock_parameters yields call to client with
        expected_data.
        '''
        mock_payment = gen_payment()
        mock_payment.id = 'f988e0c5-ea44-4111-a7f2-39ecf6af9840'
        mock_client.return_value.get_payment_by_key.return_value = mock_payment

        mock_stripe_refund = stripe.Refund()
        stripe_refund_json = EXAMPLE_RETURNED_ORDER_STRIPE_SIGNAL_PAYLOAD['stripe_refund']
        mock_stripe_refund.update(stripe_refund_json)

        _ = returned_uut(*self.unpack_for_uut(EXAMPLE_RETURNED_ORDER_STRIPE_SIGNAL_PAYLOAD))
        logger.info('mock_client().mock_calls: %s', mock_client().mock_calls)

        mock_client().create_return_payment_transaction.assert_called_once_with(
            payment_id=mock_payment.id,
            payment_version=mock_payment.version,
            refund=mock_stripe_refund
        )

    def test_full_refund_already_exists(self, mock_client):
        """
        Check if the payment already has a full refund, the task logs the
        appropriate messages and skips creating a refund transaction.
        """
        mock_payment = gen_payment_with_multiple_transactions(
            TransactionType.CHARGE, 4900,
            TransactionType.REFUND, 4900
        )
        mock_payment.id = 'f988e0c5-ea44-4111-a7f2-39ecf6af9840'

        mock_client.return_value.get_payment_by_key.return_value = mock_payment

        payment_intent_id = EXAMPLE_RETURNED_ORDER_STRIPE_SIGNAL_PAYLOAD['payment_intent_id']

        with patch('commerce_coordinator.apps.commercetools.tasks.logger') as mock_logger:
            result = refund_from_stripe_task(*self.unpack_for_uut(EXAMPLE_RETURNED_ORDER_STRIPE_SIGNAL_PAYLOAD))
            self.assertIsNone(result)

            # Check that both info messages were logged in the expected order
            mock_logger.info.assert_has_calls([
                call(
                    f"[refund_from_stripe_task] "
                    f"Initiating creation of CT payment's refund transaction object "
                    f"for payment Intent ID {payment_intent_id}."),
                call(f"[refund_from_stripe_task] Event 'charge.refunded' received, "
                     f"but Payment with ID {mock_payment.id} "
                     f"already has a full refund. Skipping task to add refund transaction")
            ])

    @patch('commerce_coordinator.apps.commercetools.tasks.logger')
    def test_exception_handling(self, mock_logger, mock_client):
        '''
        Check if an error in the client results in a logged error
        and the exception being raised.
        '''
        mock_payment = gen_payment()
        mock_payment.id = 'f988e0c5-ea44-4111-a7f2-39ecf6af9840'
        mock_client.return_value.get_payment_by_key.return_value = mock_payment
        mock_client().create_return_payment_transaction.side_effect = CommercetoolsError(
            message="Could not create return transaction",
            errors="Some error message",
            response={},
            correlation_id="123456"
        )

        with self.assertRaises(CommercetoolsError):
            returned_uut(*self.unpack_for_uut(EXAMPLE_RETURNED_ORDER_STRIPE_SIGNAL_PAYLOAD))

        mock_logger.error.assert_called_once_with(
            f"[refund_from_stripe_task] Unable to create CT payment's refund transaction "
            f"object for [ {mock_payment.id} ] "
            f"on Stripe refund {EXAMPLE_RETURNED_ORDER_STRIPE_CLIENT_PAYLOAD['stripe_refund']['id']} "
            f"with error Some error message and correlation id 123456"
        )


@patch("commerce_coordinator.apps.commercetools.tasks.CommercetoolsAPIClient")
class ReturnedOrderfromPaypalTaskTest(TestCase):
    """Returned Order From PayPal Task Test"""

    @staticmethod
    def unpack_for_uut(values):
        """Unpack the dictionary in the order required for the UUT"""
        return (
            values["paypal_capture_id"],
            values["refund"],
            values["order_number"],
        )

    def setUp(self):
        User.objects.create(username="test-user", lms_user_id=4)
        self.mock_parameters = {
            "refund": {
                "id": "paypal_refund_123",
                "amount": "49.99",
                "currency": "USD",
                "status": "COMPLETED",
            },
            "order_number": "2U-123456",
            "paypal_capture_id": "capture_abc123",
        }

    def test_correct_arguments_passed(self, mock_client):
        """
        Check calling uut with mock_parameters yields call to client with
        expected_data.
        """
        mock_payment = gen_payment()
        mock_payment.id = "f988e0c5-ea44-4111-a7f2-39ecf6af9840"
        mock_client.return_value.get_payment_by_transaction_interaction_id.return_value = (
            mock_payment
        )

        _ = paypal_uut(*self.unpack_for_uut(self.mock_parameters))
        logger.info("mock_client().mock_calls: %s", mock_client().mock_calls)

        mock_client().create_return_payment_transaction.assert_called_once_with(
            payment_id=mock_payment.id,
            payment_version=mock_payment.version,
            refund=self.mock_parameters["refund"],
            psp="paypal_edx",
        )

    def test_full_refund_already_exists(self, mock_client):
        """
        Check if the payment already has a full refund, the task logs the
        appropriate messages and skips creating a refund transaction.
        """
        mock_payment = gen_payment_with_multiple_transactions(
            TransactionType.CHARGE, 4900, TransactionType.REFUND, 4900
        )
        mock_payment.id = "f988e0c5-ea44-4111-a7f2-39ecf6af9840"

        mock_client.return_value.get_payment_by_transaction_interaction_id.return_value = (
            mock_payment
        )

        with patch(
            "commerce_coordinator.apps.commercetools.tasks.logger"
        ) as mock_logger:
            result = paypal_uut(*self.unpack_for_uut(self.mock_parameters))
            self.assertIsNone(result)

            refund_id = self.mock_parameters["refund"].get("id")
            # Check that the info message was logged
            mock_logger.info.assert_called_with(
                f"PayPal PAYMENT.CAPTURE.REFUNDED event received, but Payment with ID {mock_payment.id} "
                f"already has a refund with ID: {refund_id}. Skipping task to add refund transaction."
            )

    @patch("commerce_coordinator.apps.commercetools.tasks.logger")
    def test_exception_handling(self, mock_logger, mock_client):
        """
        Check if an error in the client results in a logged error
        and the exception being raised.
        """
        mock_payment = gen_payment()
        mock_payment.id = "f988e0c5-ea44-4111-a7f2-39ecf6af9840"
        mock_payment.key = "paypal_payment_key_123"
        mock_client.return_value.get_payment_by_transaction_interaction_id.return_value = (
            mock_payment
        )
        mock_client().create_return_payment_transaction.side_effect = (
            CommercetoolsError(
                message="Could not create return transaction",
                errors="Some error message",
                response={},
                correlation_id="123456",
            )
        )

        with self.assertRaises(CommercetoolsError):
            paypal_uut(*self.unpack_for_uut(self.mock_parameters))

        refund_id = self.mock_parameters["refund"].get("id")
        mock_logger.error.assert_called_once_with(
            f"[refund_from_paypal_task] Unable to create CT payment's refund "
            f"transaction object for payment {mock_payment.key} "
            f"on PayPal refund {refund_id} "
            f"with error Some error message and correlation id 123456"
        )


@patch("commerce_coordinator.apps.commercetools.tasks.CommercetoolsAPIClient")
class ReturnedOrderfromMobileTaskTest(TestCase):
    """Returned Order From Mobile Task Test"""

    @staticmethod
    def unpack_for_uut(values):
        """Unpack the dictionary in the order required for the UUT"""
        return (
            values["payment_interface"],
            values["refund"],
            values["http_request"],
        )

    def setUp(self):
        User.objects.create(username="test-user", lms_user_id=4)
        self.mock_parameters = {
            "refund": {
                "id": "mobile_refund_123",
                "amount": "99.99",
                "currency": "USD",
                "status": "completed",
            },
            "payment_interface": "ios_iap_edx",
            "http_request": Mock(),
        }

    def test_correct_arguments_passed(self, mock_client):
        """
        Check calling uut with mock_parameters yields call to client with
        expected_data.
        """
        mock_payment = gen_payment()
        mock_payment.id = "f988e0c5-ea44-4111-a7f2-39ecf6af9840"
        mock_client.return_value.get_payment_by_transaction_interaction_id.return_value = (
            mock_payment
        )
        mock_client.return_value.find_order_with_unprocessed_return_for_payment.return_value = (
            None
        )

        _ = mobile_uut(*self.unpack_for_uut(self.mock_parameters))
        logger.info("mock_client().mock_calls: %s", mock_client().mock_calls)

        mock_client().create_return_payment_transaction.assert_called_once_with(
            payment_id=mock_payment.id,
            payment_version=mock_payment.version,
            refund=self.mock_parameters["refund"],
            psp=self.mock_parameters["payment_interface"],
        )

    def test_android_payment_amount_adjustment(self, mock_client):
        """
        Check that for Android payments, the amount is adjusted from the payment amount planned.
        """
        mock_payment = gen_payment()
        mock_payment.id = "android-payment-id"
        mock_payment.amount_planned = Money(cent_amount=5000, currency_code="USD")
        mock_client.return_value.get_payment_by_transaction_interaction_id.return_value = (
            mock_payment
        )
        mock_client.return_value.find_order_with_unprocessed_return_for_payment.return_value = (
            None
        )

        self.mock_parameters["payment_interface"] = "android_iap_edx"

        _ = mobile_uut(*self.unpack_for_uut(self.mock_parameters))

        # Verify the refund amount was updated
        refund = self.mock_parameters["refund"].copy()
        refund["amount"] = 5000
        refund["currency"] = "USD"

        mock_client().create_return_payment_transaction.assert_called_once_with(
            payment_id=mock_payment.id,
            payment_version=mock_payment.version,
            refund=refund,
            psp="android_iap_edx",
        )

    def test_with_unprocessed_return(self, mock_client):
        """
        Check that update_return_payment_state_after_successful_refund is called when
        an unprocessed return is found.
        """
        mock_payment = gen_payment()
        mock_payment.id = "f988e0c5-ea44-4111-a7f2-39ecf6af9840"
        mock_client.return_value.get_payment_by_transaction_interaction_id.return_value = (
            mock_payment
        )

        # Mock return of a valid OrderWithReturnInfo
        class MockOrderWithReturnInfo:
            order_id = "order-123"
            order_version = 2
            return_line_item_return_ids = ["return-456"]

        mock_client.return_value.find_order_with_unprocessed_return_for_payment.return_value = (
            MockOrderWithReturnInfo()
        )

        # Set up create_return_payment_transaction to return the payment
        mock_client().create_return_payment_transaction.return_value = mock_payment

        _ = mobile_uut(*self.unpack_for_uut(self.mock_parameters))

        # Verify update_return_payment_state_after_successful_refund was called
        mock_client().update_return_payment_state_after_successful_refund.assert_called_once_with(
            interaction_id=self.mock_parameters["refund"]["id"],
            payment_intent_id=self.mock_parameters["refund"]["id"],
            payment=mock_payment,
            order_id="order-123",
            order_version=2,
            return_line_item_return_ids=["return-456"],
            refunded_line_item_refunds={},
            return_line_entitlement_ids={},
            should_transition_state=False
        )

    def test_full_refund_already_exists(self, mock_client):
        """
        Check if the payment already has a full refund, the task logs the
        appropriate messages and continues processing for order updates.
        """
        mock_payment = gen_payment_with_multiple_transactions(
            TransactionType.CHARGE, 4900, TransactionType.REFUND, 4900
        )
        mock_payment.id = "f988e0c5-ea44-4111-a7f2-39ecf6af9840"
        mock_client.return_value.get_payment_by_transaction_interaction_id.return_value = (
            mock_payment
        )
        mock_client.return_value.find_order_with_unprocessed_return_for_payment.return_value = (
            None
        )

        with patch(
            "commerce_coordinator.apps.commercetools.tasks.logger"
        ) as mock_logger:
            _ = mobile_uut(*self.unpack_for_uut(self.mock_parameters))

            refund_id = self.mock_parameters["refund"].get("id")
            # Check that the info message was logged
            mock_logger.info.assert_called_with(
                "[refund_from_mobile_task] Mobile refund event received, but Payment "
                f"with ID {mock_payment.id} already has a refund with ID: {refund_id}."
                "Skipping addition of refund transaction."
            )

            # Verify create_return_payment_transaction was NOT called
            mock_client().create_return_payment_transaction.assert_not_called()

    @patch("commerce_coordinator.apps.commercetools.tasks.logger")
    def test_exception_handling(self, mock_logger, mock_client):
        """
        Check if an error in the client results in a logged error
        and the exception being raised.
        """
        mock_payment = gen_payment()
        mock_payment.id = "f988e0c5-ea44-4111-a7f2-39ecf6af9840"
        mock_payment.key = "mobile_payment_key_123"
        mock_client.return_value.get_payment_by_transaction_interaction_id.return_value = (
            mock_payment
        )
        mock_client().create_return_payment_transaction.side_effect = (
            CommercetoolsError(
                message="Could not create return transaction",
                errors="Some error message",
                response={},
                correlation_id="123456",
            )
        )

        with self.assertRaises(CommercetoolsError):
            mobile_uut(*self.unpack_for_uut(self.mock_parameters))

        refund_id = self.mock_parameters["refund"].get("id")
        mock_logger.error.assert_called_once_with(
            f"[refund_from_mobile_task] Unable to refund for mobile for "
            f"transaction ID: {refund_id} of payment processor: ios_iap_edx."
            f"with error Some error message and correlation id 123456"
        )

    @patch("commerce_coordinator.apps.commercetools.tasks.revoke_line_mobile_order_signal")
    def test_signal_sent_after_refund(self, mock_signal, mock_client):
        """
        Test that the revoke_line_mobile_order_signal is sent after processing
        a mobile refund with the correct parameters.
        """
        # Set up payment mock
        mock_payment = gen_payment()
        mock_payment.id = "mobile-payment-id-123"
        mock_client.return_value.get_payment_by_transaction_interaction_id.return_value = mock_payment
        mock_client.return_value.find_order_with_unprocessed_return_for_payment.return_value = None
        mock_client.return_value.create_return_payment_transaction.return_value = mock_payment

        # Call the task function
        mobile_uut(*self.unpack_for_uut(self.mock_parameters))

        # Assert that the signal was sent with the correct parameters
        mock_signal.send_robust.assert_called_once_with(
            sender=mobile_uut,
            payment_id=mock_payment.id
        )

    @patch("commerce_coordinator.apps.commercetools.tasks.EcommerceAPIClient")
    @patch("commerce_coordinator.apps.commercetools.tasks.is_redirect_to_legacy_enabled")
    def test_ios_legacy_redirect_when_payment_not_found(self, mock_redirect_enabled, mock_ecommerce_client, mock_client):
        """
        Test that refund_for_ios is called when payment is not found and legacy redirect is enabled for iOS.
        """
        # Set up mocks
        mock_client.return_value.get_payment_by_transaction_interaction_id.return_value = None
        mock_redirect_enabled.return_value = True

        # Create a mock request with body
        mock_request = Mock()
        mock_request.body = b'{"test": "data"}'
        self.mock_parameters["http_request"] = mock_request

        # Call the task function
        result = mobile_uut(*self.unpack_for_uut(self.mock_parameters))

        # Verify EcommerceAPIClient was called with correct parameters
        mock_ecommerce_client.assert_called_once()
        mock_ecommerce_client_instance = mock_ecommerce_client.return_value
        mock_ecommerce_client_instance.refund_for_ios.assert_called_once_with(payload=mock_request.body)

        # Verify the function returns None when payment is not found
        self.assertIsNone(result)

    @patch("commerce_coordinator.apps.commercetools.tasks.EcommerceAPIClient")
    @patch("commerce_coordinator.apps.commercetools.tasks.is_redirect_to_legacy_enabled")
    def test_ios_legacy_redirect_not_called_when_redirect_disabled(self, mock_redirect_enabled, mock_ecommerce_client, mock_client):
        """
        Test that refund_for_ios is NOT called when legacy redirect is disabled for iOS.
        """
        # Set up mocks
        mock_client.return_value.get_payment_by_transaction_interaction_id.return_value = None
        mock_redirect_enabled.return_value = False

        # Create a mock request with body
        mock_request = Mock()
        mock_request.body = b'{"test": "data"}'
        self.mock_parameters["http_request"] = mock_request

        # Call the task function
        result = mobile_uut(*self.unpack_for_uut(self.mock_parameters))

        # Verify EcommerceAPIClient was NOT called
        mock_ecommerce_client.assert_not_called()

        # Verify the function returns None when payment is not found
        self.assertIsNone(result)

    @patch("commerce_coordinator.apps.commercetools.tasks.EcommerceAPIClient")
    @patch("commerce_coordinator.apps.commercetools.tasks.is_redirect_to_legacy_enabled")
    def test_ios_legacy_redirect_not_called_for_android_payment(self, mock_redirect_enabled, mock_ecommerce_client, mock_client):
        """
        Test that refund_for_ios is NOT called for Android payments even when legacy redirect is enabled.
        """
        # Set up mocks
        mock_client.return_value.get_payment_by_transaction_interaction_id.return_value = None
        mock_redirect_enabled.return_value = True

        # Change payment interface to Android
        self.mock_parameters["payment_interface"] = "android_iap_edx"

        # Create a mock request with body
        mock_request = Mock()
        mock_request.body = b'{"test": "data"}'
        self.mock_parameters["http_request"] = mock_request

        # Call the task function
        result = mobile_uut(*self.unpack_for_uut(self.mock_parameters))

        # Verify EcommerceAPIClient was NOT called for Android
        mock_ecommerce_client.assert_not_called()

        # Verify the function returns None when payment is not found
        self.assertIsNone(result)

    @patch("commerce_coordinator.apps.commercetools.tasks.EcommerceAPIClient")
    @patch("commerce_coordinator.apps.commercetools.tasks.is_redirect_to_legacy_enabled")
    def test_ios_legacy_redirect_not_called_when_payment_found(self, mock_redirect_enabled, mock_ecommerce_client, mock_client):
        """
        Test that refund_for_ios is NOT called when payment is found, even if legacy redirect is enabled.
        """
        # Set up mocks - payment is found
        mock_payment = gen_payment()
        mock_payment.id = "f988e0c5-ea44-4111-a7f2-39ecf6af9840"
        mock_client.return_value.get_payment_by_transaction_interaction_id.return_value = mock_payment
        mock_client.return_value.find_order_with_unprocessed_return_for_payment.return_value = None
        mock_client.return_value.create_return_payment_transaction.return_value = mock_payment
        mock_redirect_enabled.return_value = True

        # Create a mock request with body
        mock_request = Mock()
        mock_request.body = b'{"test": "data"}'
        self.mock_parameters["http_request"] = mock_request

        # Call the task function
        result = mobile_uut(*self.unpack_for_uut(self.mock_parameters))

        # Verify EcommerceAPIClient was NOT called since payment was found
        mock_ecommerce_client.assert_not_called()

        # Verify the function returns the payment when payment is found
        self.assertEqual(result, mock_payment)

    @patch("commerce_coordinator.apps.commercetools.tasks.EcommerceAPIClient")
    @patch("commerce_coordinator.apps.commercetools.tasks.is_redirect_to_legacy_enabled")
    def test_ios_legacy_redirect_with_empty_request_body(self, mock_redirect_enabled, mock_ecommerce_client, mock_client):
        """
        Test that refund_for_ios is called with empty body when request body is empty.
        """
        # Set up mocks
        mock_client.return_value.get_payment_by_transaction_interaction_id.return_value = None
        mock_redirect_enabled.return_value = True

        # Create a mock request with empty body
        mock_request = Mock()
        mock_request.body = b''
        self.mock_parameters["http_request"] = mock_request

        # Call the task function
        result = mobile_uut(*self.unpack_for_uut(self.mock_parameters))

        # Verify EcommerceAPIClient was called with empty body
        mock_ecommerce_client.assert_called_once()
        mock_ecommerce_client_instance = mock_ecommerce_client.return_value
        mock_ecommerce_client_instance.refund_for_ios.assert_called_once_with(payload=b'')

        # Verify the function returns None when payment is not found
        self.assertIsNone(result)

    @patch("commerce_coordinator.apps.commercetools.tasks.EcommerceAPIClient")
    @patch("commerce_coordinator.apps.commercetools.tasks.is_redirect_to_legacy_enabled")
    def test_ios_legacy_redirect_ecommerce_client_exception(self, mock_redirect_enabled, mock_ecommerce_client, mock_client):
        """
        Test that exceptions from EcommerceAPIClient.refund_for_ios are properly raised.
        """
        # Set up mocks
        mock_client.return_value.get_payment_by_transaction_interaction_id.return_value = None
        mock_redirect_enabled.return_value = True

        # Create a mock request with body
        mock_request = Mock()
        mock_request.body = b'{"test": "data"}'
        self.mock_parameters["http_request"] = mock_request

        # Set up EcommerceAPIClient to raise an exception
        from requests.exceptions import RequestException
        mock_ecommerce_client_instance = mock_ecommerce_client.return_value
        mock_ecommerce_client_instance.refund_for_ios.side_effect = RequestException("Ecommerce API error")

        # Call the task function and expect the exception to be raised
        with self.assertRaises(RequestException):
            mobile_uut(*self.unpack_for_uut(self.mock_parameters))

        # Verify EcommerceAPIClient was called
        mock_ecommerce_client.assert_called_once()
        mock_ecommerce_client_instance.refund_for_ios.assert_called_once_with(payload=mock_request.body)


@patch("commerce_coordinator.apps.commercetools.tasks.OrderFulfillmentAPIClient")
@patch("commerce_coordinator.apps.commercetools.tasks.CommercetoolsAPIClient")
class RevokeLineMobileOrderTaskTest(TestCase):
    """Tests for the revoke_line_mobile_order_task"""

    def setUp(self):
        self.user = User.objects.create(username="test-user", lms_user_id=4)
        self.payment_id = "mobile-payment-123"

    @patch("commerce_coordinator.apps.commercetools.tasks.get_line_item_attribute")
    def test_successful_revoke_line(self, mock_get_attribute, mock_ct_client, mock_fulfillment_client):
        """Test successful execution of the revoke_line_mobile_order_task"""
        # Generate test data
        mock_order = gen_order("order-123")
        mock_order.customer_id = "customer-123"

        # Set up line item attributes
        mock_order.line_items[0].variant.attributes = [
            Mock(name="course_id", value="course-v1:MichiganX+InjuryPreventionX+1T2021"),
            Mock(name="lob", value="edx")
        ]

        # Configure the mocked get_line_item_attribute to return "verified" for mode
        mock_get_attribute.return_value = "verified"

        # Mock the customer with LMS user ID
        mock_customer = Mock()
        mock_customer.id = "customer-123"
        mock_customer.custom = Mock()
        mock_customer.custom.fields = {"edx-lms_user_id": "4", "edx-lms_user_name": "test-user"}

        # Configure client returns
        mock_ct_client.return_value.get_order_by_payment_id.return_value = mock_order
        mock_ct_client.return_value.get_customer_by_id.return_value = mock_customer

        # Execute the task
        result = revoke_line_mobile_order_task(self.payment_id)

        # Verify the OrderFulfillmentAPIClient was called with correct data
        mock_fulfillment_client.return_value.revoke_line.assert_called_once()
        call_kwargs = mock_fulfillment_client.return_value.revoke_line.call_args[1]

        self.assertEqual(call_kwargs["payload"]["edx_lms_username"], "test-user")
        self.assertEqual(
            call_kwargs["payload"]["course_run_key"], "course-v1:MichiganX+InjuryPreventionX+1T2021"
        )
        self.assertEqual(call_kwargs["payload"]["course_mode"], "verified")
        self.assertEqual(call_kwargs["payload"]["lob"], "edx")

        # Verify the task returns True on success
        self.assertTrue(result)

    def test_commercetools_error(self, mock_ct_client, mock_fulfillment_client):
        """Test handling of CommercetoolsError"""
        # Make the API client raise an error
        mock_ct_client.return_value.get_order_by_payment_id.side_effect = CommercetoolsError(
            message="Could not find order",
            errors="Order not found",
            response={},
            correlation_id="123456"
        )

        # Execute the task and verify it raises the exception
        with self.assertRaises(CommercetoolsError):
            revoke_line_mobile_order_task(self.payment_id)

        # Verify the fulfillment client was not called
        mock_fulfillment_client.return_value.revoke_line.assert_not_called()
