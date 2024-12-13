""" PayPal Pipeline Tests"""
from unittest import TestCase

from django.conf import settings
from django.test import override_settings

from commerce_coordinator.apps.paypal.pipeline import GetPayPalPaymentReceipt


class TestGetPayPalPaymentReceipt(TestCase):
    """A pytest Test case for the GetPayPalPaymentReceipt Pipeline Step"""

    @override_settings(
        PAYPAL_USER_ACTIVITY_PAGE_URL="https://paypal.com/myaccount/activities/"
    )
    def test_pipeline_step(self):
        order_number = '123'
        paypal_payment_pipe = GetPayPalPaymentReceipt("test_pipe", None)

        result: dict = paypal_payment_pipe.run_filter(
            edx_lms_user_id=1,
            psp='paypal_edx',
            payment_intent_id="00001",
            order_number=order_number
        )
        redirect_url = f"{settings.PAYPAL_USER_ACTIVITY_PAGE_URL}?free_text_search={order_number}"
        self.assertEqual(redirect_url, result['redirect_url'])
