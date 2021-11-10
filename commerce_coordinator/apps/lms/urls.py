"""
LMS app URLs
"""
from django.conf.urls import url

from commerce_coordinator.apps.lms.views import test_view

app_name = 'lms'
urlpatterns = [
    # FIXME: Test URL should be removed post proof-of-concept.
    url(r'^test/', test_view, name='lms_test'),
]
