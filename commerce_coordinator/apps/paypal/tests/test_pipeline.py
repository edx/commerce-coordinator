""" PayPal Pipeline Tests"""
from unittest import TestCase

from django.conf import settings
from django.test import override_settings

from commerce_coordinator.apps.paypal.pipeline import GetPayPalPaymentReceipt

TEST_PAYMENT_PROCESSOR_CONFIG = settings.PAYMENT_PROCESSOR_CONFIG
ACTIVITY_URL = "https://test.paypal.com/myaccount/activities/"
TEST_PAYMENT_PROCESSOR_CONFIG['edx']['paypal']['user_activity_page_url'] = ACTIVITY_URL


class TestGetPayPalPaymentReceipt(TestCase):
    """A pytest Test case for the GetPayPalPaymentReceipt Pipeline Step"""

    @override_settings(PAYMENT_PROCESSOR_CONFIG=TEST_PAYMENT_PROCESSOR_CONFIG)
    def test_pipeline_step(self):
        order_number = '123'
        paypal_payment_pipe = GetPayPalPaymentReceipt("test_pipe", None)

        result: dict = paypal_payment_pipe.run_filter(
            edx_lms_user_id=1,
            psp='paypal_edx',
            payment_intent_id="00001",
            order_number=order_number
        )
        url = settings.PAYMENT_PROCESSOR_CONFIG['edx']['paypal']['user_activity_page_url']
        redirect_url = f"{url}?free_text_search={order_number}"
        self.assertEqual(redirect_url, result['redirect_url'])
