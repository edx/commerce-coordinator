"""
frontend_app_ecommerce app URLS
"""

from django.urls import include, path

from commerce_coordinator.apps.frontend_app_ecommerce.views import UserOrdersView

app_name = 'frontend_app_ecommerce'
urlpatterns = [
    path('order_history/', UserOrdersView.as_view(), name='order_history'),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
]
