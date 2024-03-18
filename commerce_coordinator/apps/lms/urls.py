"""
LMS (edx-platform) app URLS
"""

from django.urls import path

from commerce_coordinator.apps.lms.views import OrderDetailsRedirectView, PaymentPageRedirectView

app_name = 'lms'
urlpatterns = [
    path('payment_page_redirect/', PaymentPageRedirectView.as_view(), name='payment_page_redirect'),
    path('order_details_page_redirect/', OrderDetailsRedirectView.as_view(), name='order_details_page_redirect'),
]
