"""
Demo LMS app URLs, in a real service these would be API endpoints or callback handlers.
"""

from django.urls import path

from commerce_coordinator.apps.demo_lms.views import demo_get_sample_data, demo_purchase_complete, test_view

app_name = 'demo_lms'
urlpatterns = [
    # DEMO: Test URL should be removed post proof-of-concept.
    path('test/', test_view, name='lms_test'),
    path('demo_purchase_complete/', demo_purchase_complete, name='lms_demo_purchase_complete'),

    # DEMO: Gets data from a filters pipeline
    path('demo_get_sample_data/', demo_get_sample_data, name='lms_demo_get_sample_data'),
]
