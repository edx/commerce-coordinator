import json

from django.conf import settings
from paypalserversdk.http.auth.o_auth_2 import ClientCredentialsAuthCredentials
from paypalserversdk.paypalserversdk_client import PaypalserversdkClient
from paypalserversdk.controllers.payments_controller import PaymentsController
from paypalserversdk.api_helper import ApiHelper

class PayPalClient:
    def __init__(self):
        self.paypal_client: PaypalserversdkClient = PaypalserversdkClient(
            client_credentials_auth_credentials=ClientCredentialsAuthCredentials(
                o_auth_client_id=settings.PAYMENT_PROCESSOR_CONFIG['edx']['paypal']['client_id'],
                o_auth_client_secret=settings.PAYMENT_PROCESSOR_CONFIG['edx']['paypal']['client_secret'],
            ),
        )


    def refund_order(self, capture_id):
        paypal_client = self.paypal_client
        payments_controller: PaymentsController = paypal_client.payments

        collect = {"capture_id": capture_id, "prefer": "return=representation"}
        refund_response = payments_controller.captures_refund(collect)
        print('\n\n\n\n\n refund_response.body = ', refund_response.body)
        if refund_response.body:
            response = json.loads(ApiHelper.json_serialize(refund_response.body))
            print('\n\n\n\n\n refund_order response serialized = ', response)

            return {
                "id": response.get("id"),
                "created": response.get("create_time"),
                "status": response.get("status"),
                "amount": response.get("amount").get("value"),
                "currency": response.get("amount").get("currency_code"),
            }

        return None
