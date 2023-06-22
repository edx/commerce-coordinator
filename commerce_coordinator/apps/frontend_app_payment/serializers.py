"""Serializers for frontend_app_payment service"""
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


class PaymentsSerializer(serializers.Serializer):  # pylint:disable=abstract-method
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


class GetActiveOrderOutputSerializer(serializers.Serializer):  # pylint:disable=abstract-method
    """
    Serializer for GetActiveOrderView output validation
    """
    itemTotal = serializers.CharField()
    order_total = serializers.CharField()
    adjustmentTotal = serializers.CharField()
    createdAt = serializers.DateTimeField()
    updatedAt = serializers.DateTimeField(allow_null=True)
    completedAt = serializers.DateTimeField(allow_null=True)
    currency = serializers.CharField()
    state = serializers.CharField()
    email = serializers.CharField()
    basket_id = serializers.UUIDField()
    promoTotal = serializers.CharField()
    itemCount = serializers.CharField()
    paymentState = serializers.CharField(allow_null=True)
    paymentTotal = serializers.CharField()
    user = UserSerializer()
    billingAddress = BillingAddressSerializer()
    products = ProductsSerializer(many=True)
    payments = PaymentsSerializer(many=True)
    enable_stripe_payment_processor = serializers.BooleanField(allow_null=False)
