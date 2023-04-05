"""
commerce-coordinator module.
"""
# This will make sure the Celery app is always imported when Django starts so that the Celery shared_task decorator
# will use this app.
from .celery import app as celery_app

__all__ = ('celery_app',)

# This is the canonical Commerce Coordinator version, used in setup.py and on GitHub.
__version__ = '0.2.0'
