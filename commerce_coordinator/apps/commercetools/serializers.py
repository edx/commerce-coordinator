"""Serializers for CommerceTools service"""

from commerce_coordinator.apps.core import serializers
from commerce_coordinator.apps.core.serializers import CoordinatorSerializer


class OrderSanctionedViewMessageDetailSerializer(CoordinatorSerializer):
    """
    Serializer for CommerceTools message 'detail'
    """
    id = serializers.CharField()
    resource = serializers.DictField(child=serializers.CharField())
    type = serializers.CharField(allow_null=False)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['message_id'] = representation.pop('id')
        representation['type'] = representation.pop('type')

        order_id = representation['resource'].get('id')
        if order_id:
            representation['order_id'] = order_id
        representation.pop('resource')
        return representation


class OrderSanctionedViewMessageInputSerializer(CoordinatorSerializer):
    """
    Serializer for commercetools Sanctioned View message input
    """
    detail = OrderSanctionedViewMessageDetailSerializer(allow_null=False)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation = representation.pop('detail')
        return representation


class OrderLineItemMessageDetailSerializer(CoordinatorSerializer):
    """
    Serializer for CommerceTools message 'detail'
    """
    id = serializers.CharField()
    resource = serializers.DictField(child=serializers.CharField())
    fromState = serializers.DictField(child=serializers.CharField())
    toState = serializers.DictField(child=serializers.CharField())

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['message_id'] = representation.pop('id')
        order_id = representation['resource'].get('id')
        if order_id:  # pragma no cover
            representation['order_id'] = order_id
        representation.pop('resource')
        representation['from_state'] = representation.pop('fromState')
        representation['to_state'] = representation.pop('toState')
        return representation


class OrderLineItemMessageInputSerializer(CoordinatorSerializer):
    """
    Serializer for commercetools message input
    """
    detail = OrderLineItemMessageDetailSerializer(allow_null=False)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation = representation.pop('detail')
        return representation


class OrderFulfillViewInputSerializer(CoordinatorSerializer):
    """
    Serializer for OrderFulfillView input validation.
    """
    course_id = serializers.CharField(allow_null=False)
    course_mode = serializers.CharField(allow_null=False)
    date_placed = serializers.CharField(allow_null=False)
    email_opt_in = serializers.BooleanField(allow_null=False)
    line_item_id = serializers.CharField(allow_null=False)
    item_quantity = serializers.IntegerField(allow_null=False)
    order_number = serializers.CharField(allow_null=False)
    order_id = serializers.CharField(allow_null=False)
    order_version = serializers.IntegerField(allow_null=False)
    provider_id = serializers.CharField(allow_null=True)
    source_system = serializers.CharField(allow_null=False)
    line_item_state_id = serializers.CharField(allow_null=False)
    edx_lms_user_id = serializers.IntegerField(allow_null=False)
    message_id = serializers.CharField(allow_null=False)
    product_title = serializers.CharField(allow_null=False)
    user_first_name = serializers.CharField(allow_null=True, allow_blank=True)
    user_last_name = serializers.CharField(allow_null=True, allow_blank=True)
    user_email = serializers.EmailField(allow_null=False)
    product_type = serializers.CharField(allow_null=False)
    lob = serializers.CharField(allow_null=False)
    edx_lms_username = serializers.CharField(allow_null=False)
    bundle_id = serializers.CharField(allow_null=True, required=False)


class OrderReturnedViewMessageLineItemReturnItemSerializer(CoordinatorSerializer):
    """
    Serializer for OrderReturnedView message LineItemReturnItem.
    """
    type = serializers.CharField()
    id = serializers.CharField()
    quantity = serializers.IntegerField()
    lineItemId = serializers.CharField()
    shipmentState = serializers.CharField()
    paymentState = serializers.CharField()
    lastModifiedAt = serializers.DateTimeField()
    createdAt = serializers.DateTimeField()


class OrderReturnedViewMessageReturnInfoSerializer(CoordinatorSerializer):
    """
    Serializer for OrderReturnedView message returnInfo.
    """
    items = OrderReturnedViewMessageLineItemReturnItemSerializer(many=True)


class OrderReturnedViewMessageDetailSerializer(CoordinatorSerializer):
    """
    Serializer for OrderReturnedView message detail.
    """
    id = serializers.CharField()
    resource = serializers.DictField(child=serializers.CharField())
    returnInfo = OrderReturnedViewMessageReturnInfoSerializer()

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['message_id'] = representation.pop('id')
        order_id = representation['resource'].get('id')
        if order_id:  # pragma no cover
            representation['order_id'] = order_id
        representation.pop('resource')
        return representation


class OrderReturnedViewMessageInputSerializer(CoordinatorSerializer):
    """
    Serializer for OrderReturnedView message input
    """
    detail = OrderReturnedViewMessageDetailSerializer(allow_null=False)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation = representation.pop('detail')
        return representation

    def get_return_info(self):
        """Get the return info from the message detail"""
        validated_data = self.validated_data
        detail = validated_data.get('detail', {})
        return detail.get('returnInfo', {})

    def get_return_line_items(self):
        return self.get_return_info().get('items', [])
