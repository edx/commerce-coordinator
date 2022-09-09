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

    def save(self):
        coupon_code = self.validated_data['coupon_code']
        course_id = self.validated_data['course_id']
        date_placed = self.validated_data['date_placed']
        edx_lms_user_id = self.validated_data['edx_lms_user_id']
        mode = self.validated_data['mode']
        partner_sku = self.validated_data['partner_sku']
        titan_order_uuid = self.validated_data['titan_order_uuid']
        edx_lms_username = self.validated_data['edx_lms_username']
