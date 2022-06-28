"""
Orders app URLS
"""

from django.urls import include, path

from commerce_coordinator.apps.orders.views import EcommerceUserOrdersView

app_name = 'orders'
urlpatterns = [
    path('order_history/', EcommerceUserOrdersView.as_view(), name='order_history'),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
]
