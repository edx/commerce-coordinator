"""
commerce tools app URLS
"""

from django.urls import path

from commerce_coordinator.apps.commercetools.views import OrderFulfillView

app_name = 'commercetools'
urlpatterns = [
    path('fulfill', OrderFulfillView.as_view(), name='fulfill'),
]
