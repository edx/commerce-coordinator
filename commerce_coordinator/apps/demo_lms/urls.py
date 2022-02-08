"""
LMS app URLs, in a real service these would be callback handlers
"""
from django.conf.urls import url

from commerce_coordinator.apps.lms.views import demo_purchase_complete, test_celery_signal_view, test_view

app_name = 'lms'
urlpatterns = [
    # FIXME: Test URL should be removed post proof-of-concept.
    url(r'^test/', test_view, name='lms_test'),
    url(r'^test_celery_signal/', test_celery_signal_view, name='lms_test_celery_signal'),
    url(r'^demo_purchase_complete/', demo_purchase_complete, name='lms_demo_purchase_complete'),
]
