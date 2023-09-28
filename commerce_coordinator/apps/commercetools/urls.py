"""
commercetools app URLS
"""

from django.urls import include, path

from commerce_coordinator.apps.commercetools.views import UserOrdersView

app_name = 'commercetools'
urlpatterns = [
    path('order_history/', UserOrdersView.as_view(), name='order_history'),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
]
