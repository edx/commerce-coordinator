"""
Models for Paypal app
"""
from django.db import models


class KeyValueCache(models.Model):
    cache_key = models.CharField(max_length=255, unique=True)
    cache_value = models.TextField()
