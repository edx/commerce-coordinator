"""
URLS for the titan app
"""

from django.urls import path

from .views import OrderFulfillView

app_name = 'titan'

urlpatterns = [
    path('fulfill/', OrderFulfillView.as_view(), name='order_fulfill'),
]
