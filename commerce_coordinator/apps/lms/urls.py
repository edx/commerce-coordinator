"""
LMS (edx-platform) app URLS
"""

from django.urls import include, path

from commerce_coordinator.apps.lms.views import OrderCreateView

app_name = 'lms'
urlpatterns = [
    path('order/', OrderCreateView.as_view(), name='create_order'),
]
