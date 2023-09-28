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
from django.urls import include, re_path
from rest_framework_swagger.views import get_swagger_view

from commerce_coordinator.apps.api import urls as api_urls
from commerce_coordinator.apps.commercetools import urls as orders_urls
from commerce_coordinator.apps.core import views as core_views
from commerce_coordinator.apps.demo_lms import urls as demo_lms_urls
from commerce_coordinator.apps.ecommerce import urls as ecommerce_urls
from commerce_coordinator.apps.frontend_app_ecommerce import urls as unified_orders_urls
from commerce_coordinator.apps.frontend_app_payment import urls as frontend_app_payment_urls
from commerce_coordinator.apps.lms import urls as lms_urls
from commerce_coordinator.apps.stripe import urls as stripe_urls
from commerce_coordinator.apps.titan import urls as titan_urls

admin.autodiscover()

urlpatterns = oauth2_urlpatterns + [
    re_path('', include('csrf.urls')),  # Include csrf urls from edx-drf-extensions
    re_path('^admin/', admin.site.urls),
    re_path('^api-docs/', get_swagger_view(title='commerce-coordinator API')),
    re_path('^api/', include(api_urls)),
    re_path('^auto_auth/', core_views.AutoAuth.as_view(), name='auto_auth'),
    re_path('^ecommerce/', include(ecommerce_urls), name='ecommerce'),
    re_path('^health/', core_views.health, name='health'),
    re_path('^lms/', include(lms_urls), name='lms'),
    re_path('^titan/', include(titan_urls), name='titan'),
    re_path('^orders/', include(orders_urls), name='frontend-app-ecommerce'),
    re_path('^orders/unified/', include(unified_orders_urls), name='commercetools'),
    re_path('^frontend-app-payment/', include(frontend_app_payment_urls)),
    re_path('^stripe/', include(stripe_urls)),
    # DEMO: Currently this is only test code, we may want to decouple LMS code here at some point...
    re_path('^demo_lms/', include(demo_lms_urls))
]

if settings.DEBUG and os.environ.get('ENABLE_DJANGO_TOOLBAR', False):  # pragma: no cover
    import debug_toolbar
    urlpatterns.append(re_path(r'^__debug__/', include(debug_toolbar.urls)))
