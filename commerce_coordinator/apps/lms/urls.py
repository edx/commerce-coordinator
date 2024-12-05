"""
LMS (edx-platform) app URLS
"""

from django.urls import path

from commerce_coordinator.apps.lms.views import (
    FirstTimeDiscountEligibleView,
    OrderDetailsRedirectView,
    PaymentPageRedirectView,
    RefundView,
    RetirementView
)

app_name = 'lms'
urlpatterns = [
    path('payment_page_redirect/', PaymentPageRedirectView.as_view(), name='payment_page_redirect'),
    path('order_details_page_redirect/', OrderDetailsRedirectView.as_view(), name='order_details_page_redirect'),
    path('refund/', RefundView.as_view(), name='refund'),
    path('user_retirement/', RetirementView.as_view(), name='user_retirement'),
    path('first-time-discount-eligible/', FirstTimeDiscountEligibleView.as_view(), name='first_time_discount_eligible'),
]
