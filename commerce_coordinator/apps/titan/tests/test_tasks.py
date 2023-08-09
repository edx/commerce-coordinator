"""Test Titan tasks."""
import ddt
from django.test import TestCase
from edx_django_utils.cache import TieredCache
from mock.mock import patch
from requests import HTTPError
from testfixtures import LogCapture

from commerce_coordinator.apps.titan.tasks import order_created_save_task, payment_processed_save_task

from ...core.cache import get_paid_payment_state_cache_key, get_processing_payment_state_cache_key
from ...core.constants import PaymentState
from .test_clients import ORDER_CREATE_DATA, ORDER_UUID, TitanClientMock

log_name = 'commerce_coordinator.apps.titan.tasks'


class TestOrderTasks(TestCase):
    """Titan Order Task, and integration tests."""

    @patch('commerce_coordinator.apps.titan.clients.TitanAPIClient.create_order', new_callable=TitanClientMock)
    def test_task(self, mock_create_order):
        """ Ensure that the `order_created_save_task` invokes create order as expected and has an expected return
            result.

        Args:
            mock_create_order (TitanClientMock): Titan Client Mock for its mock_create_order command.
        """
        order_created_save_task.apply(
            args=ORDER_CREATE_DATA.values()
        ).get()

        mock_create_order.assert_called_with(
            ORDER_CREATE_DATA['sku'],
            ORDER_CREATE_DATA['edx_lms_user_id'],
            ORDER_CREATE_DATA['email'],
            ORDER_CREATE_DATA['coupon_code']
        )

        values = mock_create_order.return_value.values()

        # values however should be the value expected as a return from complete_order
        self.assertEqual(list(values), [{'attributes': {'uuid': ORDER_UUID}}])


@ddt.ddt
class TestPaymentTasks(TestCase):
    """Titan payment tests."""

    @ddt.data(PaymentState.COMPLETED.value, PaymentState.FAILED.value)
    @patch('commerce_coordinator.apps.titan.clients.TitanAPIClient.update_payment')
    def test_payment_processed_save_task(self, payment_state, mock_update_payment):
        """ Ensure that the `payment_processed_save_task` invokes create update_payment as expected.

        Args:
            mock_update_payment (TitanClientMock): Titan Client Mock for its mock_update_payment command.
        """
        TieredCache.dangerous_clear_all_tiers()
        mock_update_payment.return_value = {
            'uuid': ORDER_UUID,
            'state': payment_state
        }
        payment_number = '12345'
        payment_update_params = {
            'edx_lms_user_id': 1,
            'order_uuid': ORDER_UUID,
            'payment_number': payment_number,
            'payment_state': payment_state,
            'reference_number': 'g7h52545gavgatTh',
            'provider_response_body': {'key': 'value'}
         }
        payment_processed_save_task.apply(
            kwargs=payment_update_params
        ).get()

        mock_update_payment.assert_called_with(
            **payment_update_params
        )

        payment_state_cache_key = None
        if payment_state == PaymentState.COMPLETED.value:
            payment_state_cache_key = get_paid_payment_state_cache_key(payment_number)
        if payment_state == PaymentState.FAILED.value:
            payment_state_cache_key = get_processing_payment_state_cache_key(payment_number)
        cached_response = TieredCache.get_cached_response(payment_state_cache_key)
        self.assertTrue(cached_response.is_found)

    @ddt.data(PaymentState.COMPLETED.value, PaymentState.FAILED.value)
    @patch('commerce_coordinator.apps.titan.clients.TitanAPIClient.update_payment', side_effect=HTTPError)
    def test_payment_processed_save_task_failure(self, payment_state, mock_update_payment):
        """ Ensure that the `payment_processed_save_task` logs error in case of exception.

        Args:
            mock_update_payment (TitanClientMock): Titan Client Mock for its mock_update_payment command.
        """
        TieredCache.dangerous_clear_all_tiers()
        payment_number = '12345'
        reference_number = 'g7h52545gavgatTh'
        payment_update_params = {
            'edx_lms_user_id': 1,
            'order_uuid': ORDER_UUID,
            'payment_number': payment_number,
            'payment_state': payment_state,
            'reference_number': reference_number,
            'provider_response_body': {'key': 'value'}
        }
        with LogCapture(log_name) as log_capture:
            payment_processed_save_task.apply(
                kwargs=payment_update_params
            ).get()
            log_capture.check_present(
                (
                    log_name,
                    'ERROR',
                    f'Titan payment_processed_save_task Failed with payment_number: {payment_number}, '
                    f'payment_state: {payment_state},and reference_number: {reference_number}. Exception: '
                )
            )
        mock_update_payment.assert_called_with(
            **payment_update_params
        )
        payment_state_cache_key = None
        if payment_state == PaymentState.COMPLETED.value:
            payment_state_cache_key = get_paid_payment_state_cache_key(payment_number)
        if payment_state == PaymentState.FAILED.value:
            payment_state_cache_key = get_processing_payment_state_cache_key(payment_number)
        cached_response = TieredCache.get_cached_response(payment_state_cache_key)
        self.assertFalse(cached_response.is_found)
