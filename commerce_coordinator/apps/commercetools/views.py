"""
Views for the commercetools app
"""
import json
import logging

import boto3
from botocore.exceptions import ClientError
from django.conf import settings
from django.http import JsonResponse
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from commerce_coordinator.apps.commercetools.authentication import JwtBearerAuthentication
from commerce_coordinator.apps.commercetools.constants import SOURCE_SYSTEM
from commerce_coordinator.apps.commercetools.serializers import (
    OrderLineItemMessageInputSerializer,
    OrderReturnedViewMessageInputSerializer,
    OrderSanctionedViewMessageInputSerializer
)
from commerce_coordinator.apps.commercetools.sub_messages.signals_dispatch import (
    fulfill_order_placed_message_signal,
    fulfill_order_returned_signal,
    fulfill_order_sanctioned_message_signal
)
from commerce_coordinator.apps.core.memcache import safe_key
from commerce_coordinator.apps.core.tasks import acquire_task_lock
from commerce_coordinator.apps.core.views import SingleInvocationAPIView

logger = logging.getLogger(__name__)

class TriggerOrderFulfillmentAWS(SingleInvocationAPIView):
    """Order Fulfillment View"""

    # authentication_classes = [JwtBearerAuthentication, SessionAuthentication]
    # permission_classes = [IsAdminUser]

    def get(self, request):
        """Receive a message from commercetools forwarded by aws event bridge"""

        tag = type(self).__name__

        logger.info(f'[CT-{tag}] Message received to trigger fulfillment.')


        event_bridge_client = boto3.client(
            'events',
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )

        event_bus_name = 'POC-commerce'

        event_detail = {
            "order_id": "1234",
        }

        response = event_bridge_client.put_events(
            Entries=[
                {
                    'Source': 'CC',
                    'DetailType': 'FulfillOrder',
                    'Detail': json.dumps(event_detail),
                    'EventBusName': event_bus_name
                }
            ]
        )

        logger.info(f"[CT-{tag}] EventBridge event sent. Response: {response}")

        return Response(status=status.HTTP_200_OK)

class OrderFulfillmentResponseAWS(SingleInvocationAPIView):
    """Order Fulfillment View"""

    def get_aws_secret_api_key(self):
        secret_name = settings.AWS_ORDER_FULFILLMENT_SECRET_NAME
        session = boto3.session.Session()
        client = session.client(
            service_name='secretsmanager',
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )

        try:
            # Fetch the secret value
            response = client.get_secret_value(SecretId=secret_name)

            # Secrets Manager encrypts the secrets, so decode them
            secret = json.loads(response['SecretString'])

            return secret

        except ClientError as e:
            # Implement retries
            print(f"Error retrieving secret: {e}")
            return None


    def is_authorized_aws_request(self, request):
        secret = self.get_aws_secret_api_key()
        secret_api_key_name = secret.get('api_key_name', None)
        secret_api_key_value = secret.get('api_key_value', None)

        if secret_api_key_name and secret_api_key_value:
            received_api_key_value = request.headers.get(secret_api_key_name)
            if received_api_key_value and received_api_key_value == secret_api_key_value:
                return True

        return False



    def post(self, request):
        """Receive a message from commercetools forwarded by aws event bridge"""

        print('\n\n\nrequest data', request.data)
        print('\n\n\nrequest headers', request.headers)

        if not self.is_authorized_aws_request(request):
            return JsonResponse({'error': 'Unauthorized'}, status=401)

        print('\n\n\n\n Hello, Order Fulfillment Response received!')
        return Response(status=200)


# noinspection DuplicatedCode
class OrderFulfillView(SingleInvocationAPIView):
    """Order Fulfillment View"""

    authentication_classes = [JwtBearerAuthentication, SessionAuthentication]
    permission_classes = [IsAdminUser]

    def post(self, request):
        """Receive a message from commerce tools forwarded by aws event bridge"""

        tag = type(self).__name__

        input_data = {
            **request.data
        }

        logger.info(f'[CT-{tag}] Message received from commercetools with details: {input_data}')

        message_details = OrderLineItemMessageInputSerializer(data=input_data)
        message_details.is_valid(raise_exception=True)

        order_id = message_details.data['order_id']
        line_item_state_id = message_details.data['to_state']['id']
        message_id = message_details.data['message_id']

        task_key = safe_key(key=order_id, key_prefix=tag, version='1')

        if not acquire_task_lock(task_key):
            logger.info(
                f"Task {task_key} is already running. Exiting current task. Order ID: {order_id}."
            )
            return Response(status=status.HTTP_200_OK)

        fulfill_order_placed_message_signal.send_robust(
            sender=self,
            order_id=order_id,
            line_item_state_id=line_item_state_id,
            source_system=SOURCE_SYSTEM,
            message_id=message_id
        )

        return Response(status=status.HTTP_200_OK)


# noinspection DuplicatedCode
class OrderSanctionedView(SingleInvocationAPIView):
    """View to sanction an order and deactivate the lms user"""

    authentication_classes = [JwtBearerAuthentication, SessionAuthentication]
    permission_classes = [IsAdminUser]

    def post(self, request):
        """
        Receive a message from commerce tools forwarded by aws event bridge
        to sanction order and deactivate user through LMS
        """
        tag = type(self).__name__

        input_data = {
            **request.data
        }

        logger.info(f'[CT-{tag}] Message received from commercetools with details: {input_data}')

        message_details = OrderSanctionedViewMessageInputSerializer(data=input_data)
        message_details.is_valid(raise_exception=True)

        order_id = message_details.data['order_id']
        message_id = message_details.data['message_id']

        if self._is_running(tag, order_id):  # pragma no cover
            self.meta_should_mark_not_running = False
            return Response(status=status.HTTP_200_OK)
        else:
            self.mark_running(tag, order_id)

        fulfill_order_sanctioned_message_signal.send_robust(
            sender=self,
            order_id=order_id,
            message_id=message_id
        )

        return Response(status=status.HTTP_200_OK)


# noinspection DuplicatedCode
class OrderReturnedView(SingleInvocationAPIView):
    """View to sanction an order and deactivate the lms user"""

    authentication_classes = [JwtBearerAuthentication, SessionAuthentication]
    permission_classes = [IsAdminUser]

    def post(self, request):
        """
        Receive a message from commerce tools forwarded by aws event bridge
        to sanction order and deactivate user through LMS
        """

        tag = type(self).__name__

        input_data = {
            **request.data
        }

        logger.info(f'[CT-{tag}] Message received from commercetools with details: {input_data}')

        message_details = OrderReturnedViewMessageInputSerializer(data=input_data)
        message_details.is_valid(raise_exception=True)
        order_id = message_details.data['order_id']

        return_items = message_details.get_return_line_items()
        message_id = message_details.data['message_id']

        fulfill_order_returned_signal.send_robust(
            sender=self,
            order_id=order_id,
            return_items=return_items,
            message_id=message_id
        )

        return Response(status=status.HTTP_200_OK)
