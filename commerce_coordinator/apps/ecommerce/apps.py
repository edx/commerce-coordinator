"""
App configuration for the ecommerce app.
"""

from django.apps import AppConfig


class EcommerceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'commerce_coordinator.apps.ecommerce'
