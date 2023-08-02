"""Serializers for Titan service"""
from collections import OrderedDict

from commerce_coordinator.apps.core import serializers
from commerce_coordinator.apps.core.serializers import CoordinatorSerializer


class OrderFulfillViewInputSerializer(CoordinatorSerializer):
    """
    Serializer for OrderFulfillView input validation.
    """
    course_id = serializers.CharField(allow_null=False)
    course_mode = serializers.CharField(allow_null=False)
    date_placed = serializers.UnixDateTimeField(allow_null=False)
    edx_lms_user_id = serializers.IntegerField(allow_null=False)
    email_opt_in = serializers.BooleanField(allow_null=False)
    order_number = serializers.UUIDField(allow_null=False)
    provider_id = serializers.CharField(allow_null=True)


class PaymentSerializer(CoordinatorSerializer):
    """
    Serializer for Titan Payment object.

    We feed this serializer with Titan's API Payment dict, and it is responsible transform it into a new dict
    that we use in coordinator system. We can rename key names here.
    """
    number = serializers.CharField(allow_null=False)
    orderUuid = serializers.UUIDField(allow_null=False)
    referenceNumber = serializers.CharField(allow_null=False)
    state = serializers.CharField(allow_null=False)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        ret = OrderedDict()
        ret['payment_number'] = representation['number']
        ret['order_uuid'] = representation['orderUuid']
        ret['key_id'] = representation['referenceNumber']
        ret['state'] = representation['state']
        return ret


class UserSerializer(CoordinatorSerializer):
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


class BillingAddressSerializer(CoordinatorSerializer):
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


class ProductsSerializer(CoordinatorSerializer):
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


class OrderPaymentsSerializer(CoordinatorSerializer):
    """
    Serializer for Payments object validation
    """
    amount = serializers.CharField()
    number = serializers.CharField()
    orderUuid = serializers.CharField()
    paymentDate = serializers.DateTimeField(allow_null=True)
    paymentMethodName = serializers.CharField()
    referenceNumber = serializers.CharField(allow_null=True)
    state = serializers.CharField()
    createdAt = serializers.DateTimeField()
    updatedAt = serializers.DateTimeField()

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        ret = OrderedDict()
        ret['amount'] = representation['amount']
        ret['payment_number'] = representation['number']
        ret['order_uuid'] = representation['orderUuid']
        ret['payment_date'] = representation['paymentDate']
        ret['payment_method_name'] = representation['paymentMethodName']
        ret['key_id'] = representation['referenceNumber']
        ret['state'] = representation['state']
        ret['created_at'] = representation['createdAt']
        ret['updated_at'] = representation['updatedAt']
        return ret


class TitanActiveOrderSerializer(CoordinatorSerializer):
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
    billingAddress = BillingAddressSerializer(allow_null=True)
    lineItems = ProductsSerializer(many=True)
    payments = OrderPaymentsSerializer(many=True, allow_null=True)

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
        return ret
