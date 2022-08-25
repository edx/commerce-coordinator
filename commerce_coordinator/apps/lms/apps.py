"""
App configuration for the Commerce Coordinator LMS app.
"""

from django.apps import AppConfig


class LmsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'commerce_coordinator.apps.lms'
