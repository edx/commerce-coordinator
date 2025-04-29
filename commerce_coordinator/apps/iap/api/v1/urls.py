"""
URL configuration for version 1 of the IAP API.

Defines routes for creating orders and other IAP-related endpoints.
"""

from django.urls import path
from commerce_coordinator.apps.iap.api.v1.views import CreateOrderView, PrepareCartView

app_name = 'v1'
urlpatterns = [
    path('prepare-cart/', PrepareCartView.as_view(), name='prepare_cart'),
    path('create-order/', CreateOrderView.as_view(), name='create_order'),
]
