"""
InAppPurchase app URLS
"""

from django.urls import path

from commerce_coordinator.apps.iap.views import AndroidRefundView, IOSRefundView, MobileCreateOrderView

app_name = "iap"
urlpatterns = [
    path("create-order/", MobileCreateOrderView.as_view(), name="create_order"),
    path("android/refund/", AndroidRefundView.as_view(), name="android_refund"),
    path("ios/refund/", IOSRefundView.as_view(), name="ios_refund"),
]
