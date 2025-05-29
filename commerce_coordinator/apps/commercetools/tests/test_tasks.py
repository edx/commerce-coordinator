"""
Commercetools app Task Tests
"""

import logging
from unittest.mock import call, patch

import stripe
from commercetools import CommercetoolsError
from commercetools.platform.models import Money, TransactionType
from django.test import TestCase

from commerce_coordinator.apps.commercetools.tasks import (
    fulfillment_completed_update_ct_line_item_task,
    refund_from_mobile_task,
    refund_from_paypal_task,
    refund_from_stripe_task
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
        and None returned.
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
        and None returned.
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

        result = paypal_uut(*self.unpack_for_uut(self.mock_parameters))
        self.assertIsNone(result)

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
                f"Mobile refund event received, but Payment with ID {mock_payment.id} "
                f"already has a refund with ID: {refund_id}. "
                "Skipping addition of refund transaction."
            )

            # Verify create_return_payment_transaction was NOT called
            mock_client().create_return_payment_transaction.assert_not_called()

    @patch("commerce_coordinator.apps.commercetools.tasks.logger")
    def test_exception_handling(self, mock_logger, mock_client):
        """
        Check if an error in the client results in a logged error
        and None returned.
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

        result = mobile_uut(*self.unpack_for_uut(self.mock_parameters))
        self.assertIsNone(result)

        refund_id = self.mock_parameters["refund"].get("id")
        mock_logger.error.assert_called_once_with(
            f"[refund_from_mobile_task] Unable to create CT payment's refund "
            f"transaction object for payment {mock_payment.key} "
            f"on mobile refund {refund_id} "
            f"with error Some error message and correlation id 123456"
        )
