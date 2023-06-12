"""
Tests for the stripe views.
"""
import logging

import ddt
import mock
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from testfixtures import LogCapture

from commerce_coordinator.apps.core.constants import PaymentState
from commerce_coordinator.apps.core.tests.utils import name_test
from commerce_coordinator.apps.stripe.constants import StripeEventType

User = get_user_model()
log = logging.getLogger(__name__)
log_name = 'commerce_coordinator.apps.stripe.views'


@ddt.ddt
class WebhooksViewTests(APITestCase):
    """ Tests StripeWebhooksView """

    def setUp(self):
        super().setUp()
        self.url = reverse('stripe:stripe_webhook')
        self.client.enforce_csrf_checks = True
        self.mock_header = {
            'HTTP_STRIPE_SIGNATURE': 't=1674755157,v1=a5e6655d0f41076ca3056517727e8',
        }
        self.mock_stripe_event = mock.Mock()

    @ddt.data('get', 'put', 'patch', 'head')
    def test_method_not_allowed(self, http_method):
        """
        Verify the view only accepts POST HTTP method.
        """
        response = getattr(self.client, http_method)(self.url)
        self.assertEqual(response.status_code, 405)

    @mock.patch('stripe.Webhook.construct_event', side_effect=ValueError("Invalid payload"))
    def test_stripe_event_value_error(self, __):
        """
        Verify an exception is raised if there is an issue with the Stripe Event from unexpected payload.
        """
        with LogCapture(log_name) as log_capture:
            response = self.client.post(
                self.url, **self.mock_header
            )
            self.assertEqual(response.status_code, 400)
            log_capture.check_present(
                (
                    log_name,
                    'ERROR',
                    'StripeWebhooksView failed with Invalid payload'
                )
            )

    def test_stripe_signature_verification_error(self):
        """
        Verify an exception is raised if there is any issue with verifying the stripe header/endpoint secret.
        """
        with LogCapture(log_name) as log_capture:
            response = self.client.post(
                self.url, **self.mock_header
            )
            self.assertEqual(response.status_code, 403)
            log_capture.check_present(
                (
                    log_name,
                    'ERROR',
                    'StripeWebhooksView SignatureVerificationError: No signatures found matching the expected '
                    'signature for payload'
                )
            )

    @ddt.data(
        name_test(
            "test payment success event",
            (StripeEventType.PAYMENT_SUCCESS.value, PaymentState.COMPLETED.value, status.HTTP_200_OK)
        ),
        name_test(
            "test payment failure",
            (StripeEventType.PAYMENT_FAILED.value, PaymentState.FAILED.value, status.HTTP_200_OK)
        ),
        name_test(
            "test event not handled by the webhook",
            ('account_updated', None, status.HTTP_422_UNPROCESSABLE_ENTITY),
        )
    )
    @ddt.unpack
    @mock.patch('commerce_coordinator.apps.titan.signals.payment_processed_save_task.delay')
    @mock.patch('stripe.Webhook.construct_event')
    def test_handled_webhook_event(
        self,
        event_type,
        expected_payment_state,
        expected_status,
        mock_construct_event,
        mock_payment_processed_save_task
    ):
        """
        Verify the expected task triggered for the known handled event types.
        """
        amount = 10000
        payment_intent_id = 'pi_789dummy'
        payment_number = 123456
        self.mock_stripe_event.type = event_type
        self.mock_stripe_event.data.object.amount = amount
        self.mock_stripe_event.data.object.metadata.payment_number = payment_number
        self.mock_stripe_event.data.object.id = payment_intent_id
        mock_construct_event.return_value = self.mock_stripe_event
        with LogCapture(log_name) as log_capture:
            response = self.client.post(self.url, **self.mock_header)
            self.assertEqual(response.status_code, expected_status)
            if expected_status == status.HTTP_200_OK:
                log_capture.check_present(
                    (
                        log_name,
                        'INFO',
                        f'[Stripe webhooks] event {event_type} with amount {amount} and '
                        f'payment intent ID [{payment_intent_id}].',
                    )
                )
                mock_payment_processed_save_task.assert_called_with(
                    payment_number, expected_payment_state, payment_intent_id
                )
            else:
                mock_payment_processed_save_task.assert_not_called()
