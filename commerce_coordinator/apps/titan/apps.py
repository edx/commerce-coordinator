"""
App configuration for the Commerce Coordinator titan app.
"""

from django.apps import AppConfig


class TitanConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'commerce_coordinator.apps.titan'
