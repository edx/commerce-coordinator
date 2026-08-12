"""
Tests for the stripe views.
"""
import logging

import ddt
import mock
from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from stripe.stripe_object import StripeObject
from testfixtures import LogCapture

from commerce_coordinator.apps.core.tests.utils import name_test
from commerce_coordinator.apps.stripe.constants import StripeEventType
from commerce_coordinator.apps.stripe.views import WebhookView

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

    @mock.patch('stripe.Webhook.construct_event')
    @mock.patch('commerce_coordinator.apps.stripe.views.payment_succeeded_commercetools_signal.send_robust')
    def test_ct_payment_succeeded_fires_signal(self, mock_ct_signal, mock_construct_event):
        """
        Verify payment_succeeded_commercetools_signal is emitted for
        payment_intent.succeeded with source_system=commercetools.
        """
        pi_id = 'pi_ct_test_123'
        self.mock_stripe_event.type = StripeEventType.PAYMENT_SUCCESS.value
        metadata = {'source_system': 'commercetools', 'ct_cart_id': 'cart-uuid'}
        self.mock_stripe_event.data.object.id = pi_id
        self.mock_stripe_event.data.object.metadata = StripeObject()
        self.mock_stripe_event.data.object.metadata.update(metadata)
        self.mock_stripe_event.data.object.amount = 4900
        mock_construct_event.return_value = self.mock_stripe_event

        response = self.client.post(
            self.url, data={}, format='json', **self.mock_header
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_ct_signal.assert_called_once_with(
            sender=WebhookView,
            payment_intent_id=pi_id,
        )

    @mock.patch('stripe.Webhook.construct_event')
    @mock.patch('commerce_coordinator.apps.stripe.views.payment_succeeded_commercetools_signal.send_robust')
    @mock.patch.object(WebhookView, '_is_running', return_value=True)
    def test_ct_payment_succeeded_single_invocation_short_circuits(
        self, mock_is_running, mock_ct_signal, mock_construct_event
    ):
        """Duplicate CT success delivery short-circuits via SingleInvocation."""
        pi_id = 'pi_ct_dup'
        self.mock_stripe_event.type = StripeEventType.PAYMENT_SUCCESS.value
        metadata = {'source_system': 'commercetools', 'ct_cart_id': 'cart-uuid'}
        self.mock_stripe_event.data.object.id = pi_id
        self.mock_stripe_event.data.object.metadata = StripeObject()
        self.mock_stripe_event.data.object.metadata.update(metadata)
        self.mock_stripe_event.data.object.amount = 4900
        mock_construct_event.return_value = self.mock_stripe_event

        response = self.client.post(
            self.url, data={}, format='json', **self.mock_header
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_is_running.assert_called()
        mock_ct_signal.assert_not_called()

    @mock.patch('stripe.Webhook.construct_event')
    @mock.patch('commerce_coordinator.apps.stripe.views.payment_succeeded_commercetools_signal.send_robust')
    def test_ct_payment_failed_returns_200_no_signal(self, mock_ct_signal, mock_construct_event):
        """
        Verify payment_intent.payment_failed with source_system=commercetools
        returns 200 but does NOT fire the CT succeeded signal.
        """
        self.mock_stripe_event.type = StripeEventType.PAYMENT_FAILED.value
        metadata = {'source_system': 'commercetools', 'ct_cart_id': 'cart-uuid'}
        self.mock_stripe_event.data.object.id = 'pi_ct_fail'
        self.mock_stripe_event.data.object.metadata = StripeObject()
        self.mock_stripe_event.data.object.metadata.update(metadata)
        self.mock_stripe_event.data.object.amount = 4900
        mock_construct_event.return_value = self.mock_stripe_event

        response = self.client.post(
            self.url, data={}, format='json', **self.mock_header
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_ct_signal.assert_not_called()

    @mock.patch('stripe.Webhook.construct_event')
    @mock.patch('commerce_coordinator.apps.stripe.views.payment_processed_signal.send_robust')
    @mock.patch('commerce_coordinator.apps.stripe.views.payment_succeeded_commercetools_signal.send_robust')
    def test_legacy_payment_succeeded_fires_processed_signal(
        self, mock_ct_signal, mock_processed_signal, mock_construct_event
    ):
        """
        Verify legacy source_system still fires payment_processed_signal,
        not the CT signal.
        """
        pi_id = 'pi_legacy'
        source_system = settings.PAYMENT_PROCESSOR_CONFIG['edx']['stripe']['source_system_identifier']
        self.mock_stripe_event.type = StripeEventType.PAYMENT_SUCCESS.value
        metadata = {
            'source_system': source_system,
            'edx_lms_user_id': '123',
            'order_number': 'EDX-000001',
            'payment_number': 'PAY-001',
        }
        self.mock_stripe_event.data.object.id = pi_id
        self.mock_stripe_event.data.object.metadata = StripeObject()
        self.mock_stripe_event.data.object.metadata.update(metadata)
        self.mock_stripe_event.data.object.amount = 4900
        self.mock_stripe_event.data.object.currency = 'usd'
        mock_construct_event.return_value = self.mock_stripe_event

        response = self.client.post(
            self.url, data={}, format='json', **self.mock_header
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_ct_signal.assert_not_called()
        mock_processed_signal.assert_called_once()

    @mock.patch('stripe.Webhook.construct_event')
    @mock.patch('commerce_coordinator.apps.stripe.views.payment_processed_signal.send_robust')
    @mock.patch('commerce_coordinator.apps.stripe.views.payment_succeeded_commercetools_signal.send_robust')
    def test_unknown_source_system_skips_both_signals(
        self, mock_ct_signal, mock_processed_signal, mock_construct_event
    ):
        """
        Verify that an unrecognized source_system returns 200
        but does not fire any signal.
        """
        self.mock_stripe_event.type = StripeEventType.PAYMENT_SUCCESS.value
        metadata = {'source_system': 'unknown_system'}
        self.mock_stripe_event.data.object.id = 'pi_unknown'
        self.mock_stripe_event.data.object.metadata = StripeObject()
        self.mock_stripe_event.data.object.metadata.update(metadata)
        self.mock_stripe_event.data.object.amount = 4900
        mock_construct_event.return_value = self.mock_stripe_event

        response = self.client.post(
            self.url, data={}, format='json', **self.mock_header
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_ct_signal.assert_not_called()
        mock_processed_signal.assert_not_called()

    @ddt.data(
        name_test(
            "Test 2U order refund and correct source_system",
            ('2U-123456', False, True, None)
        ),
        name_test(
            "Test edx order refund and correct source_system",
            ('EDX-123456', True, False, None)
        ),
        name_test(
            "Test edx order refund and incorrect source_system",
            ('EDX-123456', True, False, 'unknown_source')
        ),
    )
    @ddt.unpack
    @mock.patch('stripe.Webhook.construct_event')
    @mock.patch('commerce_coordinator.apps.stripe.views.payment_refunded_signal.send_robust')
    @mock.patch('commerce_coordinator.apps.stripe.views.is_legacy_order')
    @mock.patch('commerce_coordinator.apps.stripe.views.is_commercetools_stripe_refund')
    def test_payment_refunded_event(
        self,
        order_number,
        is_legacy_order,
        is_ct_order,
        source_system,
        mock_is_ct_refund,
        mock_is_legacy,
        mock_refund_task,
        mock_construct_event
    ):
        """
        Verify the payment_refunded_signal is sent correctly for PAYMENT_REFUNDED event.
        """
        expected_status = status.HTTP_200_OK
        payment_intent_id = 'pi_789dummy'
        refund_data = {
            'id': "re_1Nispe2eZvKYlo2Cd31jOCgZ",
            'amount': 1000,
            'charge': "ch_1NirD82eZvKYlo2CIvbtLWuY",
            'created': 1692942318,
            'currency': "usd",
            'payment_intent': "pi_3PNWMsH4caH7G0X109NekCG5",
            'status': "succeeded",
        }
        default_source_system = settings.PAYMENT_PROCESSOR_CONFIG['edx']['stripe']['source_system_identifier']
        source_system = source_system or default_source_system
        self.mock_stripe_event.type = StripeEventType.PAYMENT_REFUNDED.value
        self.mock_stripe_event.data.object.payment_intent = payment_intent_id
        self.mock_stripe_event.data.object.refunds.data = [refund_data]
        metadata = {
            'order_number': order_number,
            'source_system': source_system
        }
        body = {'data': {'object': {'refunds': {'data': []}, 'metadata': metadata}}}
        self.mock_stripe_event.data.object.metadata = StripeObject()
        self.mock_stripe_event.data.object.metadata.update(metadata)
        mock_construct_event.return_value = self.mock_stripe_event
        mock_is_legacy.return_value = is_legacy_order
        mock_is_ct_refund.return_value = is_ct_order

        response = self.client.post(self.url, data=body, format='json', **self.mock_header)
        self.assertEqual(response.status_code, expected_status)

        if not is_legacy_order:
            mock_refund_task.assert_called_with(
                sender=WebhookView,
                payment_intent_id=payment_intent_id,
                stripe_refund=refund_data,
                order_number=order_number
            )
        else:
            mock_refund_task.assert_not_called()
