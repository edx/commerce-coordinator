"""
Models for Paypal app
"""
from django.db import models


class KeyValueCache(models.Model):
    key = models.CharField(max_length=255, unique=True)
    value = models.TextField()
