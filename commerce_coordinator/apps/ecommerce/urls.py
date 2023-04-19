"""
ecommerce app URLS
"""

from django.urls import include, path

from commerce_coordinator.apps.ecommerce.views import OrderCreateView, OrderFulfillView, RedeemEnrollmentCodeView

app_name = 'ecommerce'
urlpatterns = [
    path('redeem_enrollment_code/', RedeemEnrollmentCodeView.as_view(), name='redeem_enrollment_code'),
    path('order/', OrderCreateView.as_view(), name='create_order'),
    path('orders/fulfill', OrderFulfillView.as_view(), name='fulfill_order'),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
]
