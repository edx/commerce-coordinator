"""
frontend_app_payment app URLS
"""

from django.urls import include, path

from commerce_coordinator.apps.frontend_app_payment.views import GetActiveOrderView

app_name = 'frontend_app_payment'
urlpatterns = [
    path('order/', GetActiveOrderView.as_view(), name='order'),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
]