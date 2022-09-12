"""
commerce-coordinator URL Configuration.

The `urlpatterns` list routes URLs to views. For more information please see:
https://docs.djangoproject.com/en/2.2/topics/http/urls/

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
from django.urls import include, path
from rest_framework_swagger.views import get_swagger_view

from commerce_coordinator.apps.api import urls as api_urls
from commerce_coordinator.apps.core import views as core_views
from commerce_coordinator.apps.demo_lms import urls as demo_lms_urls
from commerce_coordinator.apps.ecommerce import urls as ecommerce_urls
from commerce_coordinator.apps.frontend_app_ecommerce import urls as orders_urls
from commerce_coordinator.apps.lms import urls as lms_urls
from commerce_coordinator.apps.titan import urls as titan_urls

admin.autodiscover()

urlpatterns = oauth2_urlpatterns + [
    path('', include('csrf.urls')),  # Include csrf urls from edx-drf-extensions
    path('admin/', admin.site.urls),
    path('api-docs/', get_swagger_view(title='commerce-coordinator API')),
    path('api/', include(api_urls)),
    path('auto_auth/', core_views.AutoAuth.as_view(), name='auto_auth'),
    path('ecommerce/', include(ecommerce_urls), name='ecommerce'),
    path('lms/', include(lms_urls), name='lms'),
    path('health/', core_views.health, name='health'),
    path('titan/', include(titan_urls), name='titan'),
    path('orders/', include(orders_urls)),
    # DEMO: Currently this is only test code, we may want to decouple LMS code here at some point...
    path('demo_lms/', include(demo_lms_urls))
]

if settings.DEBUG and os.environ.get('ENABLE_DJANGO_TOOLBAR', False):  # pragma: no cover
    # Disable pylint import error because we don't install django-debug-toolbar
    # for CI build
    import debug_toolbar  # pylint: disable=import-error,useless-suppression
    urlpatterns.append(path('__debug__/', include(debug_toolbar.urls)))
