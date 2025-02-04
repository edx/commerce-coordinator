import os
from os.path import abspath, dirname, join

from corsheaders.defaults import default_headers as corsheaders_default_headers

from commerce_coordinator.settings.utils import get_logger_config

# Settings not defined in this file are not overridden by ArgoCD on Deployment.

# PATH vars
PROJECT_ROOT = join(abspath(dirname(__file__)), "..")


def root(*path_fragments):
    return join(abspath(PROJECT_ROOT), *path_fragments)


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('COMMERCE_COORDINATOR_SECRET_KEY', 'insecure-secret-key')

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
    'commerce_coordinator.apps.ecommerce.apps.EcommerceConfig',
    'commerce_coordinator.apps.frontend_app_ecommerce.apps.FrontendAppEcommerceConfig',
    'commerce_coordinator.apps.frontend_app_payment.apps.FrontendAppPaymentConfig',
    'commerce_coordinator.apps.lms.apps.LmsConfig',
    'commerce_coordinator.apps.stripe.apps.StripeConfig',
    'commerce_coordinator.apps.paypal.apps.PayPalConfig',
    'commerce_coordinator.apps.commercetools',
)

INSTALLED_APPS += THIRD_PARTY_APPS
INSTALLED_APPS += PROJECT_APPS

# CACHE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#caches
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}
# END CACHE CONFIGURATION

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
    # Outputs monitoring metrics for a request.
    'edx_rest_framework_extensions.middleware.RequestCustomAttributesMiddleware',
    # Ensures proper DRF permissions in support of JWTs
    'edx_rest_framework_extensions.auth.jwt.middleware.EnsureJWTAuthSettingsMiddleware',

    # /!\ The docs want this to be last. /!\ :
    #     https://github.com/openedx/edx-django-utils/tree/master/edx_django_utils/cache#tieredcachemiddleware
    # Enables force_django_cache_miss functionality for TieredCache.
    'edx_django_utils.cache.middleware.TieredCacheMiddleware',
)


DEFAULT_TIMEOUT = 30 * 60  # Value is in seconds
# End Cache Configuration

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
# https://docs.djangoproject.com/en/3.2/ref/settings/#databases
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

# Celery
CELERY_TASK_DEFAULT_EXCHANGE = 'commerce_coordinator'
CELERY_TASK_DEFAULT_QUEUE = 'commerce_coordinator.default'
CELERY_TASK_DEFAULT_ROUTING_KEY = 'commerce_coordinator'

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
# See: https://docs.djangoproject.com/en/3.2/ref/settings/#templates
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
SESSION_COOKIE_NAME = 'commerce_coordinator_sessionid'
CSRF_COOKIE_NAME = 'commerce_coordinator_csrftoken'
LANGUAGE_COOKIE_NAME = 'commerce_coordinator_language'
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
BACKEND_SERVICE_EDX_OAUTH2_PROVIDER_URL = 'replace-me'
BACKEND_SERVICE_EDX_OAUTH2_KEY = 'replace-me'
BACKEND_SERVICE_EDX_OAUTH2_SECRET = 'replace-me'

JWT_AUTH = {
    'JWT_AUTH_HEADER_PREFIX': 'JWT',
    'JWT_ISSUER': 'http://127.0.0.1:8000/oauth2',
    'JWT_ALGORITHM': 'HS256',
    'JWT_VERIFY_EXPIRATION': True,
    'JWT_PAYLOAD_GET_USERNAME_HANDLER': lambda d: d.get('preferred_username'),
    'JWT_LEEWAY': 1,
    'JWT_DECODE_HANDLER': 'edx_rest_framework_extensions.auth.jwt.decoder.jwt_decode_handler',
    'JWT_PUBLIC_SIGNING_JWK_SET': None,
    'JWT_AUTH_COOKIE': 'edx-jwt-cookie',
    'JWT_AUTH_COOKIE_HEADER_PAYLOAD': 'edx-jwt-cookie-header-payload',
    'JWT_AUTH_COOKIE_SIGNATURE': 'edx-jwt-cookie-signature',
}

# Request the user's permissions in the ID token
EXTRA_SCOPE = ['permissions']

# TODO Set this to another (non-staff, ideally) path.
LOGIN_REDIRECT_URL = '/admin/'

# Set legacy credentials to access edX services.
EDX_API_KEY = 'replace-me'

# Set token credentials for non-edX services.
TITAN_API_KEY = 'replace-me'

# Set OAuth2 credentials for non-edX services.
TITAN_OAUTH2_PROVIDER_URL = 'replace-me'
TITAN_OAUTH2_KEY = 'replace-me'
TITAN_OAUTH2_SECRET = 'replace-me'
# END AUTHENTICATION CONFIGURATION

# DRF CONFIGURATION
REST_FRAMEWORK = {
    'EXCEPTION_HANDLER': 'commerce_coordinator.apps.core.middleware.log_drf_exceptions',
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'edx_rest_framework_extensions.auth.jwt.authentication.JwtAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    ),
    'DEFAULT_THROTTLE_CLASSES': (
        'rest_framework.throttling.UserRateThrottle',
    ),
    'DEFAULT_THROTTLE_RATES': {
        'user': '75/minute',
        'get_payment': '1000/hour',
    },
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
    'commerce_coordinator.apps.commercetools.signals.fulfill_order_placed_signal': [
        'commerce_coordinator.apps.lms.signal_handlers.fulfill_order_placed_send_enroll_in_course',
    ],
    'commerce_coordinator.apps.lms.signals.fulfillment_completed_signal': [
        'commerce_coordinator.apps.commercetools.signals.fulfill_order_completed_send_line_item_state',
    ],
    'commerce_coordinator.apps.commercetools.sub_messages.signals_dispatch.fulfill_order_placed_message_signal': [
        'commerce_coordinator.apps.commercetools.sub_messages.signals_delayed.fulfill_order_placed_message_signal',
    ],
    'commerce_coordinator.apps.commercetools.sub_messages.signals_dispatch.fulfill_order_sanctioned_message_signal': [
        'commerce_coordinator.apps.commercetools.sub_messages.signals_delayed.fulfill_order_sanctioned_message_signal',
    ],
    'commerce_coordinator.apps.commercetools.sub_messages.signals_dispatch.fulfill_order_returned_signal': [
        'commerce_coordinator.apps.commercetools.sub_messages.signals_delayed.fulfill_order_returned_signal',
    ],
    'commerce_coordinator.apps.stripe.signals.payment_refunded_signal': [
        'commerce_coordinator.apps.commercetools.signals.refund_from_stripe',
    ],
    "commerce_coordinator.apps.paypal.signals.payment_refunded_signal": [
        "commerce_coordinator.apps.commercetools.signals.refund_from_paypal",
    ],
}

# Default timeouts for requests
# (See https://docs.python-requests.org/en/master/user/advanced/#timeouts for more info.)
REQUEST_CONNECT_TIMEOUT_SECONDS = 3.05
REQUEST_READ_TIMEOUT_SECONDS = 5

# Special timeout for fulfillment
FULFILLMENT_TIMEOUT = 7

# API URLs
COMMERCE_COORDINATOR_URL = 'http://localhost:8140'
ECOMMERCE_URL = 'http://localhost:18130'
ECOMMERCE_ADD_TO_BASKET_API_PATH = '/basket/add/'
ECOMMERCE_ORDER_DETAILS_DASHBOARD_PATH = '/dashboard/orders/'
TITAN_URL = 'replace-me'

# Timeout for enterprise client
ENTERPRISE_CLIENT_TIMEOUT = os.environ.get('ENTERPRISE_CLIENT_TIMEOUT', 15)

# Filters
OPEN_EDX_FILTERS_CONFIG = {
    "org.edx.coordinator.frontend_app_ecommerce.order.history.requested.v1": {
        "fail_silently": False,  # Coordinator filters should NEVER be allowed to fail silently
        "pipeline": [
            'commerce_coordinator.apps.ecommerce.pipeline.GetEcommerceOrders',  # old system
            'commerce_coordinator.apps.commercetools.pipeline.GetCommercetoolsOrders',  # new system
        ]
    },
    "org.edx.coordinator.lms.payment.page.redirect.requested.v1": {
        "fail_silently": False,  # Coordinator filters should NEVER be allowed to fail silently
        "pipeline": [
            'commerce_coordinator.apps.rollout.pipeline.GetActiveOrderManagementSystem',
            'commerce_coordinator.apps.commercetools_frontend.pipeline.GetCommercetoolsRedirectUrl',
            'commerce_coordinator.apps.frontend_app_payment.pipeline.GetPaymentMFERedirectUrl'
        ]
    },
    "org.edx.coordinator.frontend_app_ecommerce.order.receipt_url.requested.v1": {
        "fail_silently": False,  # Coordinator filters should NEVER be allowed to fail silently
        "pipeline": [
            'commerce_coordinator.apps.rollout.pipeline.DetermineActiveOrderManagementSystemByOrderNumber',
            'commerce_coordinator.apps.ecommerce.pipeline.GetLegacyEcommerceReceiptRedirectUrl',
            'commerce_coordinator.apps.rollout.pipeline.HaltIfRedirectUrlProvided',
            'commerce_coordinator.apps.commercetools.pipeline.FetchOrderDetailsByOrderNumber',
            'commerce_coordinator.apps.stripe.pipeline.GetPaymentIntentReceipt',
            'commerce_coordinator.apps.paypal.pipeline.GetPayPalPaymentReceipt'
        ]
    },
    "org.edx.coordinator.lms.order.refund.requested.v1": {
        "fail_silently": False,  # Coordinator filters should NEVER be allowed to fail silently
        "pipeline": [
            'commerce_coordinator.apps.rollout.pipeline.DetermineActiveOrderManagementSystemByOrderID',
            'commerce_coordinator.apps.commercetools.pipeline.CreateReturnForCommercetoolsOrder',
        ]
    },
    "org.edx.coordinator.commercetools.order.refund.requested.v1": {
        "fail_silently": False,  # Coordinator filters should NEVER be allowed to fail silently
        "pipeline": [
            'commerce_coordinator.apps.rollout.pipeline.DetermineActiveOrderManagementSystemByOrderID',
            'commerce_coordinator.apps.commercetools.pipeline.FetchOrderDetailsByOrderID',
            'commerce_coordinator.apps.stripe.pipeline.RefundPaymentIntent',
            'commerce_coordinator.apps.paypal.pipeline.RefundPayPalPayment',
            'commerce_coordinator.apps.commercetools.pipeline.CreateReturnPaymentTransaction',
            'commerce_coordinator.apps.commercetools.pipeline.UpdateCommercetoolsOrderReturnPaymentStatus',
        ]
    },
    "org.edx.coordinator.lms.user.retirement.requested.v1": {
        "fail_silently": False,  # Coordinator filters should NEVER be allowed to fail silently
        "pipeline": [
            'commerce_coordinator.apps.commercetools.pipeline.AnonymizeRetiredUser',
        ]
    }
}

# Carry fields from the JWT token and LMS user into the local user
EDX_DRF_EXTENSIONS = {
    "JWT_PAYLOAD_USER_ATTRIBUTE_MAPPING": {
        "administrator": "is_staff",
        "email": "email",
        "name": "full_name",
        "user_id": "lms_user_id",
    },
    "ENABLE_SET_REQUEST_USER_FOR_JWT_COOKIE": True,
}

STRIPE_WEBHOOK_ENDPOINT_SECRET = 'SET-ME-PLEASE'
PAYPAL_WEBHOOK_ID = 'SET-ME-PLEASE'

# PAYMENT PROCESSING
PAYMENT_PROCESSOR_CONFIG = {
    'edx': {
        'stripe': {
            'api_version': '2022-08-01; server_side_confirmation_beta=v1',
            'enable_telemetry': None,
            'log_level': 'info',
            'max_network_retries': 0,
            'proxy': None,
            'publishable_key': 'SET-ME-PLEASE',
            'secret_key': 'SET-ME-PLEASE',
            'source_system_identifier': 'edx/commerce_coordinator?v=1',
            'webhook_endpoint_secret': STRIPE_WEBHOOK_ENDPOINT_SECRET,
        },
        'paypal': {
            'user_activity_page_url': '',
            'paypal_webhook_id': PAYPAL_WEBHOOK_ID,
            'client_id': '',
            'client_secret': '',
            'env': 'sandbox',
        },
    },
}
# END PAYMENT PROCESSING

LMS_URL_ROOT = "http://localhost:18000"
LMS_DASHBOARD_URL = "http://localhost:18000"  # fix me
ORDER_HISTORY_URL = "http://localhost:1996"

RETIRED_USER_SALTS = ['abc', '123']

_COMMERCETOOLS_CONFIG_GEO = 'us-central1.gcp'

COMMERCETOOLS_CONFIG = {
    'projectKey': 'SET_ME',
    'clientId': 'SET_ME',
    'clientSecret': 'SET_ME',
    'authUrl': f"https://auth.{_COMMERCETOOLS_CONFIG_GEO}.commercetools.com",
    'apiUrl': f"https://api.{_COMMERCETOOLS_CONFIG_GEO}.commercetools.com",
    'importUrl': f"https://import.{_COMMERCETOOLS_CONFIG_GEO}.commercetools.com",  # Required for ImpEx
    'scopes': 'some_scope'
}

# Checkout view urls
COMMERCETOOLS_FRONTEND_URL = 'http://localhost:3000/SET-ME'

COMMERCETOOLS_MERCHANT_CENTER_ORDERS_PAGE_URL = \
    f'https://mc.{_COMMERCETOOLS_CONFIG_GEO}.commercetools.com/{COMMERCETOOLS_CONFIG["projectKey"]}/orders'


# Will be suffixed with order numbers
ECOMMERCE_RECEIPT_URL_BASE = f'{ECOMMERCE_URL}/checkout/receipt/?order_number='

# Setting to keep using deprecated pytz with Django>4
USE_DEPRECATED_PYTZ = True

# BRAZE API SETTINGS
BRAZE_API_KEY = None
BRAZE_API_SERVER = None
BRAZE_CT_ORDER_CONFIRMATION_CANVAS_ID = ''
BRAZE_CT_FULFILLMENT_UNSUPPORTED_MODE_ERROR_CANVAS_ID = ''

# SEGMENT WRITE KEY
SEGMENT_KEY = None

FAVICON_URL = "https://edx-cdn.org/v3/prod/favicon.ico"
