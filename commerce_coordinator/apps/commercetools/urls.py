"""
commercetools app URLS
"""

from django.urls import include, path

from commerce_coordinator.apps.commercetools.views import OrderFulfillView

app_name = 'commercetools'
urlpatterns = [
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    path('fulfill', OrderFulfillView.as_view(), name='fulfill'),
]