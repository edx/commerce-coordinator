"""
Orders app URLS
"""

from django.urls import path

from commerce_coordinator.apps.orders.views import redirect_user_orders__ecommerce

app_name = 'orders'
urlpatterns = [
    path('order_history/', redirect_user_orders__ecommerce, name='order_history'),
]
