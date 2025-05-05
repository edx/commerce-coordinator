"""
This module provides the `EventBridgePublisher` class, which is responsible for publishing events
to AWS EventBridge.

It uses `boto3` to interact with AWS EventBridge.

Attributes:
    event_bus_name (str): The name of the EventBridge event bus (configured in settings).
    client (boto3.client): The boto3 EventBridge client.

Usage:
    publisher = EventBridgePublisher()
    response = publisher.publish_event(
        source='OF',
        detail_type='FulfillmentResponse',
        detail={'order_id': '4321'}
    )
"""

import json
import logging
import boto3
from botocore.exceptions import BotoCoreError, ClientError
from django.conf import settings

logger = logging.getLogger(__name__)

class AWSEventBridgePublisher:
    """
    Publishes events to AWS EventBridge.

    This class handles sending events to a specified EventBridge bus. The event is sent using
    the `put_events` method without retry logic, relying on EventBridge's internal behavior
    for handling transient errors.

    Attributes:
        event_bus_name (str): The name of the EventBridge event bus.
        client (boto3.client): The boto3 EventBridge client.
    """

    def __init__(self, event_bus_name: str = None):
        self.event_bus_name = event_bus_name or settings.AWS_EVENT_BUS_NAME
        self.client = boto3.client(
            'events',
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )

    def _publish_event(self, source: str, detail_type: str, detail: dict):
        """
        Publishes an event to EventBridge.

        Args:
            source (str): The source of the event (e.g., 'OF').
            detail_type (str): The type of the event (e.g., 'FulfillmentResponse').
            detail (dict): The detailed event data to be sent.

        Returns:
            dict: The response from the EventBridge API call.

        Raises:
            AuthenticationFailed: If the event cannot be published due to issues with EventBridge.
        """
        event_payload = {
            'Source': source,
            'DetailType': detail_type,
            'Detail': json.dumps(detail),
            'EventBusName': self.event_bus_name,
        }

        return self.client.put_events(Entries=[event_payload])

    def publish_fulfillment_request_event(self, payload: dict):
        """
        Publishes the fulfillment request event to EventBridge.

        Args:
            payload (dict): The detailed event data to be sent.

        Returns:
            dict: The response from the EventBridge API call.

        Raises:
            Exception: If the event cannot be published due to issues with EventBridge.
        """
        try:
            response = self._publish_event(source='CC', detail_type='FulfillmentRequest', detail=payload)
            logger.info("[EventBridge] Fulfillment request event published successfully: %s", payload)
            return response
        except (BotoCoreError, ClientError) as err:
            logger.error(
                "[EventBridge] Fulfillment response event failed to publish. Payload: %s, Error: %s",
                payload, err
            )
            raise err
