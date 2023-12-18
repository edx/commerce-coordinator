"""
LMS (edx-platform) app URLS
"""

from django.urls import path

from commerce_coordinator.apps.lms.views import PaymentPageRedirectView

app_name = 'lms'
urlpatterns = [
    path('payment_page_redirect/', PaymentPageRedirectView.as_view(), name='payment_page_redirect'),
]
