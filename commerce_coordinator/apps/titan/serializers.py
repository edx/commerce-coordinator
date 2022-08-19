""" Serializers for data manipulated by commerce-coordinator titan API endpoints. """

from rest_framework import serializers


class OrderFulfillSerializer(serializers.Serializer):
    """ Serializer to use with instances of OrderFulfillView for order fulfillment from Titan """
    coupon_code = serializers.CharField(max_length=200)
    course_id = serializers.CharField(max_length=200)
    partner_sku = serializers.CharField(max_length=200)
    titan_order_id = serializers.IntegerField()
    user_id = serializers.IntegerField()

    def create(self, validated_data):
        # TODO: perform checks here
        return validated_data

    def update(self, instance, validated_data):
        instance.coupon_code = validated_data.get('coupon_code', instance.coupon_code)
        instance.course_id = validated_data.get('course_id', instance.course_id)
        instance.partner_sku = validated_data.get('partner_sku', instance.partner_sku)
        instance.titan_order_id = validated_data.get('titan_order_id', instance.titan_order_id)
        instance.user_id = validated_data.get('user_id', instance.user_id)
        return instance
