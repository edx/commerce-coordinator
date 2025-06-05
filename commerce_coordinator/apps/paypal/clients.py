"""PayPal client"""
import json

from django.conf import settings
from paypalserversdk.api_helper import ApiHelper
from paypalserversdk.configuration import Environment
from paypalserversdk.controllers.payments_controller import PaymentsController
from paypalserversdk.http.auth.o_auth_2 import ClientCredentialsAuthCredentials
from paypalserversdk.paypal_serversdk_client import PaypalServersdkClient


class PayPalClient:
    """
    PayPal SDK client to call PayPal APIs.
    """
    def __init__(self):
        self.paypal_client: PaypalServersdkClient = PaypalServersdkClient(
            client_credentials_auth_credentials=ClientCredentialsAuthCredentials(
                o_auth_client_id=settings.PAYMENT_PROCESSOR_CONFIG['edx']['paypal']['client_id'],
                o_auth_client_secret=settings.PAYMENT_PROCESSOR_CONFIG['edx']['paypal']['client_secret'],
            ),
            environment=(
                Environment.SANDBOX
                if settings.PAYMENT_PROCESSOR_CONFIG['edx']['paypal']['env'] == 'sandbox'
                else Environment.PRODUCTION
            ),
        )

    def refund_order(self, capture_id, amount):
        """
        Capture PayPal refund.

        Args:
            capture_id (str): The identifier of the PayPal order to capture refund.

        Returns:
            The response from PayPal.
        """

        paypal_client = self.paypal_client
        payments_controller: PaymentsController = paypal_client.payments

        collect = {
            "capture_id": capture_id,
            "prefer": "return=representation",
            "body": {
                "amount": {
                    "value": amount,
                    "currency_code": "USD"
                }
            }
        }
        refund_response = payments_controller.refund_captured_payment(collect)

        if refund_response.body:
            response = json.loads(ApiHelper.json_serialize(refund_response.body))
            return {
                "id": response.get("id"),
                "created": response.get("create_time"),
                "status": response.get("status"),
                "amount": response.get("amount").get("value"),
                "currency": response.get("amount").get("currency_code"),
            }

        return None
