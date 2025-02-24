"""
commerce_coordinator URL Configuration.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/

Examples:

Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')

Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')

Including another URLconf
    1. Add an import:  from blog import urls as blog_urls
    2. Add a URL to urlpatterns:  url(r'^blog/', include(blog_urls))
"""

import os

from auth_backends.urls import oauth2_urlpatterns
from django.conf import settings
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path, re_path
from django.views.generic import RedirectView
from rest_framework import status
from rest_framework_swagger.views import get_swagger_view

from commerce_coordinator.apps.api import urls as api_urls
from commerce_coordinator.apps.commercetools import urls as commercetools_urls
from commerce_coordinator.apps.core import views as core_views
from commerce_coordinator.apps.demo_lms import urls as demo_lms_urls
from commerce_coordinator.apps.ecommerce import urls as ecommerce_urls
from commerce_coordinator.apps.frontend_app_ecommerce import urls as unified_orders_urls
from commerce_coordinator.apps.frontend_app_payment import urls as frontend_app_payment_urls
from commerce_coordinator.apps.lms import urls as lms_urls
from commerce_coordinator.apps.paypal import urls as paypal_urls
from commerce_coordinator.apps.stripe import urls as stripe_urls
from commerce_coordinator.settings.base import FAVICON_URL

admin.autodiscover()

urlpatterns = oauth2_urlpatterns + [
    # Standard IDA Handlers
    re_path('', include('csrf.urls')),  # Include csrf urls from edx-drf-extensions
    re_path(r'^admin/', admin.site.urls),
    # Use the same auth views for all logins, including those originating from the browsable API.
    re_path('api-auth/', include((oauth2_urlpatterns, 'rest_framework'))),
    re_path(r'^api-docs/', get_swagger_view(title='commerce-coordinator API')),
    re_path(r'^api/', include(api_urls)),
    re_path(r'^auto_auth/', core_views.AutoAuth.as_view(), name='auto_auth'),
    re_path(r'^health/?', core_views.health, name='health'),

    # Local Django Apps
    re_path(r'^ecommerce/', include(ecommerce_urls), name='ecommerce'),
    re_path(r'^lms/', include(lms_urls), name='lms'),
    re_path(r'^commercetools/', include(commercetools_urls), name='commercetools'),
    re_path(r'^orders/', include(commercetools_urls, namespace="commercetools_orders_fwd")),
    re_path(r'^orders/unified/', include(unified_orders_urls), name='frontend_app_ecommerce'),
    re_path(r'^frontend-app-payment/', include(frontend_app_payment_urls)),
    re_path(r'^stripe/', include(stripe_urls)),
    re_path(r'^paypal/', include(paypal_urls)),

    # Browser automated hits, this will limit 404s in logging
    re_path(r'^$', lambda r: JsonResponse(data=[
        "Welcome to Commerce Coordinator",
        "This is an API app that provides a backend for Commerce.",
    ], status=status.HTTP_200_OK, safe=False), name='root'),

    path('favicon.ico', RedirectView.as_view(url=FAVICON_URL), name='favicon'),

    # DEMO: Currently this is only test code, we may want to decouple LMS code here at some point...
    re_path(r'^demo_lms/', include(demo_lms_urls))
]

if settings.DEBUG and os.environ.get('ENABLE_DJANGO_TOOLBAR', False):  # pragma: no cover
    import debug_toolbar

    urlpatterns.append(re_path(r'^__debug__/', include(debug_toolbar.urls)))
