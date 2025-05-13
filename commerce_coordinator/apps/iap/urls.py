"""
InAppPurchase app URLS
"""

from django.urls import path
from commerce_coordinator.apps.iap.views import MobileCreateOrderView

urlpatterns = [
    path("create-order/", MobileCreateOrderView.as_view(), name="create_order"),
]
