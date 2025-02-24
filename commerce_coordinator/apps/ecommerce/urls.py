"""
ecommerce app URLS
"""

from django.urls import include, path

app_name = 'ecommerce'
urlpatterns = [
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
]
