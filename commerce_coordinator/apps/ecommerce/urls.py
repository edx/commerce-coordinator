"""
ecommerce app URLS
"""

from django.urls import include, path

from commerce_coordinator.apps.ecommerce.views import RedeemEnrollmentCodeView

app_name = 'ecommerce'
urlpatterns = [
    path('redeem_enrollment_code/', RedeemEnrollmentCodeView.as_view(), name='redeem_enrollment_code'),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
]
