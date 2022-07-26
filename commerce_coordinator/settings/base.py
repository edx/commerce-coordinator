import os
from os.path import abspath, dirname, join

from corsheaders.defaults import default_headers as corsheaders_default_headers

from commerce_coordinator.settings.utils import get_logger_config


# PATH vars
def here(*x):
    return join(abspath(dirname(__file__)), *x)


PROJECT_ROOT = here("..")


def root(*x):
    return join(abspath(PROJECT_ROOT), *x)


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('COMMERCE-COORDINATOR_SECRET_KEY', 'insecure-secret-key')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = []

# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'release_util',
)

THIRD_PARTY_APPS = (
    'corsheaders',
    'csrf.apps.CsrfAppConfig',  # Enables frontend apps to retrieve CSRF tokens
    'edx_django_utils.user',
    'rest_framework',
    'rest_framework_swagger',
    'social_django',
    'waffle',
)

PROJECT_APPS = (
    'commerce_coordinator.apps.core.apps.CoreConfig',
    'commerce_coordinator.apps.api',
)

INSTALLED_APPS += THIRD_PARTY_APPS
INSTALLED_APPS += PROJECT_APPS

MIDDLEWARE = (
    # Resets RequestCache utility for added safety.
    'edx_django_utils.cache.middleware.RequestCacheMiddleware',
    # Monitoring middleware should be immediately after RequestCacheMiddleware
    'edx_django_utils.monitoring.DeploymentMonitoringMiddleware',  # python and django version
    'edx_django_utils.monitoring.CookieMonitoringMiddleware',  # cookie names (compliance) and sizes
    'edx_django_utils.monitoring.CachedCustomMonitoringMiddleware',  # support accumulate & increment
    'edx_django_utils.monitoring.MonitoringMemoryMiddleware',  # memory usage
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'edx_rest_framework_extensions.auth.jwt.middleware.JwtRedirectToLoginIfUnauthenticatedMiddleware',
    'edx_rest_framework_extensions.auth.jwt.middleware.JwtAuthCookieMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'social_django.middleware.SocialAuthExceptionMiddleware',
    'waffle.middleware.WaffleMiddleware',
    # Enables force_django_cache_miss functionality for TieredCache.
    'edx_django_utils.cache.middleware.TieredCacheMiddleware',
    # Outputs monitoring metrics for a request.
    'edx_rest_framework_extensions.middleware.RequestCustomAttributesMiddleware',
    # Ensures proper DRF permissions in support of JWTs
    'edx_rest_framework_extensions.auth.jwt.middleware.EnsureJWTAuthSettingsMiddleware',
)

# Enable CORS
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = corsheaders_default_headers + (
    'use-jwt-cookie',
)
CORS_ORIGIN_WHITELIST = []

ROOT_URLCONF = 'commerce_coordinator.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'commerce_coordinator.wsgi.application'

# Database
# https://docs.djangoproject.com/en/2.2/ref/settings/#databases
# Set this value in the environment-specific files (e.g. local.py, production.py, test.py)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.',
        'NAME': '',
        'USER': '',
        'PASSWORD': '',
        'HOST': '',  # Empty for localhost through domain sockets or '127.0.0.1' for localhost through TCP.
        'PORT': '',  # Set to empty string for default.
    }
}

# New DB primary keys default to an IntegerField.
DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

# Internationalization
# https://docs.djangoproject.com/en/dev/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

LOCALE_PATHS = (
    root('conf', 'locale'),
)


# MEDIA CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#media-root
MEDIA_ROOT = root('media')

# See: https://docs.djangoproject.com/en/dev/ref/settings/#media-url
MEDIA_URL = '/media/'
# END MEDIA CONFIGURATION


# STATIC FILE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#static-root
STATIC_ROOT = root('assets')

# See: https://docs.djangoproject.com/en/dev/ref/settings/#static-url
STATIC_URL = '/static/'

# See: https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#std:setting-STATICFILES_DIRS
STATICFILES_DIRS = (
    root('static'),
)

# TEMPLATE CONFIGURATION
# See: https://docs.djangoproject.com/en/2.2/ref/settings/#templates
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'APP_DIRS': True,
        'DIRS': (
            root('templates'),
        ),
        'OPTIONS': {
            'context_processors': (
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.request',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.contrib.messages.context_processors.messages',
                'commerce_coordinator.apps.core.context_processors.core',
            ),
            'debug': True,  # Django will only display debug pages if the global DEBUG setting is set to True.
        }
    },
]
# END TEMPLATE CONFIGURATION


# COOKIE CONFIGURATION
# The purpose of customizing the cookie names is to avoid conflicts when
# multiple Django services are running behind the same hostname.
# Detailed information at: https://docs.djangoproject.com/en/dev/ref/settings/
SESSION_COOKIE_NAME = 'commerce-coordinator_sessionid'
CSRF_COOKIE_NAME = 'commerce-coordinator_csrftoken'
LANGUAGE_COOKIE_NAME = 'commerce-coordinator_language'
# END COOKIE CONFIGURATION

CSRF_COOKIE_SECURE = False
CSRF_TRUSTED_ORIGINS = []

# AUTHENTICATION CONFIGURATION
LOGIN_URL = '/login/'
LOGOUT_URL = '/logout/'

AUTH_USER_MODEL = 'core.User'

AUTHENTICATION_BACKENDS = (
    'auth_backends.backends.EdXOAuth2',
    'django.contrib.auth.backends.ModelBackend',
)

ENABLE_AUTO_AUTH = False
AUTO_AUTH_USERNAME_PREFIX = 'auto_auth_'

SOCIAL_AUTH_STRATEGY = 'auth_backends.strategies.EdxDjangoStrategy'

# Set these to the correct values for your OAuth2 provider (e.g., LMS)
SOCIAL_AUTH_EDX_OAUTH2_KEY = 'replace-me'
SOCIAL_AUTH_EDX_OAUTH2_SECRET = 'replace-me'
SOCIAL_AUTH_EDX_OAUTH2_URL_ROOT = 'replace-me'
SOCIAL_AUTH_EDX_OAUTH2_LOGOUT_URL = 'replace-me'
BACKEND_SERVICE_EDX_OAUTH2_KEY = 'replace-me'
BACKEND_SERVICE_EDX_OAUTH2_SECRET = 'replace-me'

JWT_AUTH = {
    'JWT_AUTH_HEADER_PREFIX': 'JWT',
    'JWT_ISSUER': 'http://127.0.0.1:8140/oauth2',
    'JWT_ALGORITHM': 'HS256',
    'JWT_VERIFY_EXPIRATION': True,
    'JWT_PAYLOAD_GET_USERNAME_HANDLER': lambda d: d.get('preferred_username'),
    'JWT_LEEWAY': 1,
    'JWT_DECODE_HANDLER': 'edx_rest_framework_extensions.auth.jwt.decoder.jwt_decode_handler',
    'JWT_PUBLIC_SIGNING_JWK_SET': None,
    'JWT_AUTH_COOKIE': 'edx-jwt-cookie',
    'JWT_AUTH_COOKIE_HEADER_PAYLOAD': 'edx-jwt-cookie-header-payload',
    'JWT_AUTH_COOKIE_SIGNATURE': 'edx-jwt-cookie-signature',
    'JWT_AUTH_REFRESH_COOKIE': 'edx-jwt-refresh-cookie',
}

# Request the user's permissions in the ID token
EXTRA_SCOPE = ['permissions']

# TODO Set this to another (non-staff, ideally) path.
LOGIN_REDIRECT_URL = '/admin/'
# END AUTHENTICATION CONFIGURATION

# DRF CONFIGURATION
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'edx_rest_framework_extensions.auth.jwt.authentication.JwtAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
}
# END DRF CONFIGURATION

# OPENEDX-SPECIFIC CONFIGURATION
PLATFORM_NAME = 'Your Platform Name Here'
# END OPENEDX-SPECIFIC CONFIGURATION

# Set up logging for development use (logging to stdout)
LOGGING = get_logger_config(debug=DEBUG)

#####################################################################
# Commerce Coordinator Signal Configuration
#
# The keys are instances of CoordinatorSignal in any installed app
# and the values are Django signal receiver functions from any
# installed app to be called when the given signal is dispatched.
# These mappings are bound and enforced in
# core.apps.CoreConfig.ready() which is run on Django startup.
#####################################################################
CC_SIGNALS = {
    # DEMO: This configuration is just for proof-of-concept and can
    # be removed once we have real signals
    'commerce_coordinator.apps.core.signals.test_signal': [
        'commerce_coordinator.apps.demo_lms.signals.test_receiver',
        'commerce_coordinator.apps.core.signals.test_receiver_exception',
        'commerce_coordinator.apps.core.signals.test_celery_task',
    ],
    'commerce_coordinator.apps.demo_lms.signals.purchase_complete_signal': [
        'commerce_coordinator.apps.demo_lms.signals.demo_purchase_complete_order_history',
        'commerce_coordinator.apps.demo_lms.signals.demo_purchase_complete_send_confirmation_email',
        'commerce_coordinator.apps.demo_lms.signals.demo_purchase_complete_enroll_in_course',
    ],
    'commerce_coordinator.apps.demo_lms.signals.enroll_learner_signal': [
        'commerce_coordinator.apps.demo_lms.signals.demo_enroll_learner_in_course',
    ],
}

# Default timeouts for requests
# (See https://docs.python-requests.org/en/master/user/advanced/#timeouts for more info.)
REQUEST_CONNECT_TIMEOUT_SECONDS = 3.05
REQUEST_READ_TIMEOUT_SECONDS = 5

# API URLs
ECOMMERCE_URL = None

# Filters PoC
OPEN_EDX_FILTERS_CONFIG = {
    "org.edx.coordinator.demo_lms.sample_data.v1": {
        "fail_silently": False,  # TODO: Coordinator filters should NEVER be allowed to fail silently
        "pipeline": [
            'commerce_coordinator.apps.demo_lms.pipeline.AddSomeData',
            'commerce_coordinator.apps.demo_lms.pipeline.AddSomeMoreData',
        ]
    },
    "org.edx.coordinator.orders.v1": {
        "fail_silently": False,  # TODO: Coordinator filters should NEVER be allowed to fail silently
        "pipeline": [
            'commerce_coordinator.apps.ecommerce.pipeline.GetEcommerceOrders',
        ]
    }
}
