"""
App configuration for the order fulfillment app.
"""


from django.apps import AppConfig


class OrderFulfillmentConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'order_fulfillment'
