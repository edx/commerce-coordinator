"""
commercetools app URLS
"""

from django.urls import include, path

app_name = 'commercetools'
urlpatterns = [
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
]
