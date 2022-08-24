"""
URLS for the LMS app
"""

from django.urls import path

from .views import EnrollmentView

app_name = 'lms'

urlpatterns = [
    path('enrollment/', EnrollmentView.as_view(), name='lms_enrollment'),
]
