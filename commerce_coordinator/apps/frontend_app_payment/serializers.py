"""Serializers for frontend_app_payment service"""
from collections import OrderedDict

from commerce_coordinator.apps.core import serializers


class GetPaymentInputSerializer(serializers.Serializer):  # pylint: disable=abstract-method
    """
    Serializer for OrderFulfillView input validation.
    """
    payment_number = serializers.CharField(allow_null=False)
    order_uuid = serializers.UUIDField(allow_null=False)
    edx_lms_user_id = serializers.IntegerField(allow_null=False)


class GetPaymentOutputSerializer(serializers.Serializer):  # pylint: disable=abstract-method
    """
    Serializer for OrderFulfillView input validation.
    """
    state = serializers.CharField(allow_null=False)


class DraftPaymentCreateViewInputSerializer(serializers.Serializer):  # pylint: disable=abstract-method
    """
    Serializer for DraftPaymentCreateView input validation.
    """
    edx_lms_user_id = serializers.IntegerField(allow_null=False)


class DraftPaymentCreateViewOutputSerializer(serializers.Serializer):  # pylint: disable=abstract-method
    """
    Serializer for DraftPaymentCreateView input validation.
    """
    payment_number = serializers.CharField(allow_null=False)
    order_uuid = serializers.UUIDField(allow_null=False)
    key_id = serializers.CharField(allow_null=False)
    state = serializers.CharField(allow_null=False)


class GetActiveOrderInputSerializer(serializers.Serializer):  # pylint: disable=abstract-method
    """
    Serializer for GetActiveOrderView input validation
    """
    edx_lms_user_id = serializers.IntegerField(allow_null=False)


class UserSerializer(serializers.Serializer):  # pylint:disable=abstract-method
    """
    Serializer for User object validation
    """
    firstName = serializers.CharField(allow_null=True)
    lastName = serializers.CharField(allow_null=True)
    email = serializers.CharField()

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        ret = OrderedDict()
        ret['first_name'] = representation['firstName']
        ret['last_name'] = representation['lastName']
        ret['email'] = representation['email']
        return ret


class BillingAddressSerializer(serializers.Serializer):  # pylint:disable=abstract-method
    """
    Serializer for Billing Address object validation
    """
    address1 = serializers.CharField(allow_null=True)
    address2 = serializers.CharField(allow_null=True)
    city = serializers.CharField(allow_null=True)
    company = serializers.CharField(allow_null=True)
    countryIso = serializers.CharField(allow_null=True)
    firstName = serializers.CharField(allow_null=True)
    lastName = serializers.CharField(allow_null=True)
    phone = serializers.CharField(allow_null=True)
    stateName = serializers.CharField(allow_null=True)
    zipcode = serializers.CharField(allow_null=True)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        ret = OrderedDict()
        ret['address_1'] = representation['address1']
        ret['address_2'] = representation['address2']
        ret['city'] = representation['city']
        ret['company'] = representation['company']
        ret['country_iso'] = representation['countryIso']
        ret['first_name'] = representation['firstName']
        ret['last_name'] = representation['lastName']
        ret['phone'] = representation['phone']
        ret['state_name'] = representation['stateName']
        ret['zipcode'] = representation['zipcode']
        return ret


class ProductsSerializer(serializers.Serializer):  # pylint:disable=abstract-method
    """
    Serializer for Products object validation
    """
    quantity = serializers.IntegerField()
    price = serializers.FloatField()
    currency = serializers.CharField()
    sku = serializers.CharField()
    title = serializers.CharField()
    courseMode = serializers.CharField()

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        ret = OrderedDict()
        ret['quantity'] = representation['quantity']
        ret['price'] = representation['price']
        ret['currency'] = representation['currency']
        ret['sku'] = representation['sku']
        ret['title'] = representation['title']
        ret['course_mode'] = representation['courseMode']
        return ret


class OrderPaymentsSerializer(serializers.Serializer):  # pylint:disable=abstract-method
    """
    Serializer for Payments object validation
    """
    amount = serializers.CharField()
    number = serializers.CharField()
    orderUuid = serializers.CharField()
    paymentDate = serializers.DateTimeField(allow_null=True)
    paymentMethodName = serializers.CharField()
    reference = serializers.CharField()
    responseCode = serializers.CharField(allow_null=True)
    state = serializers.CharField()
    createdAt = serializers.DateTimeField()
    updatedAt = serializers.DateTimeField()

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        ret = OrderedDict()
        ret['amount'] = representation['amount']
        ret['number'] = representation['number']
        ret['order_uuid'] = representation['orderUuid']
        ret['payment_date'] = representation['paymentDate']
        ret['payment_method_name'] = representation['paymentMethodName']
        ret['reference'] = representation['reference']
        ret['response_code'] = representation['responseCode']
        ret['state'] = representation['state']
        ret['created_at'] = representation['createdAt']
        ret['updated_at'] = representation['updatedAt']
        return ret


class GetActiveOrderOutputSerializer(serializers.Serializer):  # pylint:disable=abstract-method
    """
    Serializer for GetActiveOrderView output validation
    """
    itemTotal = serializers.CharField()
    total = serializers.CharField()
    adjustmentTotal = serializers.CharField()
    createdAt = serializers.DateTimeField()
    updatedAt = serializers.DateTimeField(allow_null=True)
    completedAt = serializers.DateTimeField(allow_null=True)
    currency = serializers.CharField()
    state = serializers.CharField()
    email = serializers.CharField()
    uuid = serializers.UUIDField()
    promoTotal = serializers.CharField()
    itemCount = serializers.CharField()
    paymentState = serializers.CharField(allow_null=True)
    paymentTotal = serializers.CharField()
    user = UserSerializer()
    billingAddress = BillingAddressSerializer()
    lineItems = ProductsSerializer(many=True)
    payments = OrderPaymentsSerializer(many=True, allow_null=True)
    enable_stripe_payment_processor = serializers.BooleanField(allow_null=False)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        ret = OrderedDict()
        ret['item_total'] = representation['itemTotal']
        ret['order_total'] = representation['total']
        ret['adjustment_total'] = representation['adjustmentTotal']
        ret['created_at'] = representation['createdAt']
        ret['updated_at'] = representation['updatedAt']
        ret['completed_at'] = representation['completedAt']
        ret['currency'] = representation['currency']
        ret['state'] = representation['state']
        ret['email'] = representation['email']
        ret['basket_id'] = representation['uuid']
        ret['promo_total'] = representation['promoTotal']
        ret['item_count'] = representation['itemCount']
        ret['payment_state'] = representation['paymentState']
        ret['payment_total'] = representation['paymentTotal']
        ret['user'] = representation['user']
        ret['billing_address'] = representation['billingAddress']
        ret['products'] = representation['lineItems']
        ret['payments'] = representation['payments']
        ret['enable_stripe_payment_processor'] = representation['enable_stripe_payment_processor']
        return ret
