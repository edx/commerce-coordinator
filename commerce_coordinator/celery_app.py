"""
Celery app needed to configure using Django settings, and make Celery tasks available to all of our Django apps.

https://docs.celeryproject.org/en/stable/django/first-steps-with-django.html
"""

import os

from celery import Celery

# Set the default configuration module, if one is not aleady defined.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'commerce_coordinator.settings.local')

app = Celery('commerce-coordinator')
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
