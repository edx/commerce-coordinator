"""
frontend_app_payment app URLS
"""

from django.urls import path

from commerce_coordinator.apps.frontend_app_payment.views import PaymentGetView, GetActiveOrderView

app_name = 'frontend_app_payment'
urlpatterns = [
    path('payment/', PaymentGetView.as_view(), name='get_payment'),
    path('order/', GetActiveOrderView.as_view(), name='order'),
]
