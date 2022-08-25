""" Serializers for data manipulated by commerce-coordinator titan API endpoints. """

from rest_framework import serializers


class OrderFulfillSerializer(serializers.Serializer):
    """ Serializer to use with instances of OrderFulfillView for order fulfillment from Titan """
    coupon_code = serializers.CharField(max_length=200)
    course_id = serializers.CharField(max_length=200)
    date_placed = serializers.CharField(max_length=200)
    edx_lms_user_id = serializers.IntegerField()
    mode = serializers.CharField(max_length=200)
    partner_sku = serializers.CharField(max_length=200)
    titan_order_uuid = serializers.IntegerField()
    edx_lms_username = serializers.CharField(max_length=200)

    def create(self, validated_data):
        # TODO: perform checks here
        return validated_data

    def update(self, instance, validated_data):
        instance.coupon_code = validated_data.get('coupon_code', instance.coupon_code)
        instance.course_id = validated_data.get('course_id', instance.course_id)
        instance.partner_sku = validated_data.get('partner_sku', instance.partner_sku)
        instance.mode = validated_data.get('mode', instance.mode)
        return instance
