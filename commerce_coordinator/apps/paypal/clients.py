import logging

from django.conf import settings
from paypalserversdk.http.auth.o_auth_2 import ClientCredentialsAuthCredentials
from paypalserversdk.logging.configuration.api_logging_configuration import (
    LoggingConfiguration,
    RequestLoggingConfiguration,
    ResponseLoggingConfiguration,
)
from paypalserversdk.paypalserversdk_client import PaypalserversdkClient
from paypalserversdk.controllers.orders_controller import OrdersController
from paypalserversdk.controllers.payments_controller import PaymentsController
from paypalserversdk.api_helper import ApiHelper


class PayPalClient:
    def __init__(self):
        self.paypal_client: PaypalserversdkClient = PaypalserversdkClient(
            client_credentials_auth_credentials=ClientCredentialsAuthCredentials(
                o_auth_client_id=settings.PAYMENT_PROCESSOR_CONFIG['edx']['paypal']['client_id'],
                o_auth_client_secret=settings.PAYMENT_PROCESSOR_CONFIG['edx']['paypal']['client_secret'],
            ),
            logging_configuration=LoggingConfiguration(
                log_level=logging.INFO,
                # Disable masking of sensitive headers for Sandbox testing.
                # This should be set to True (the default if unset)in production.
                mask_sensitive_headers=False,
                request_logging_config=RequestLoggingConfiguration(
                    log_headers=True, log_body=True
                ),
                response_logging_config=ResponseLoggingConfiguration(
                    log_headers=True, log_body=True
                ),
            ),
        )


    def refund_order(self, order_id):
        paypal_client = self.paypal_client
        orders_controller: OrdersController = paypal_client.orders
        payments_controller: PaymentsController = paypal_client.payments

        order = orders_controller.orders_get({"id": order_id})

        capture_id = order.body.purchase_units[0].payments.captures[0].id

        collect = {"capture_id": capture_id, "prefer": "return=minimal"}
        result = payments_controller.captures_refund(collect)

        if result.body:
            return {"paypal_capture_id": capture_id}
        
        return None
