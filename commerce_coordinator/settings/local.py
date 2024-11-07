from commerce_coordinator.settings.base import *

DEBUG = True

ALLOWED_HOSTS += (
    # Built-in alias to reach the host machine running Docker Desktop from inside a container:
    'host.docker.internal',
    'localhost',
    '.ngrok-free.app',
    '.share.zrok.io'
)

INSTALLED_APPS += (
    'commerce_coordinator.apps.demo_lms.apps.DemoLmsConfig',
)

# CORS CONFIGURATION
CORS_ORIGIN_WHITELIST = [
    'http://localhost:1996',  # frontend-app-ecommerce
    'http://localhost:1998',  # frontend-app-payment
    'https://bo1qumbnpc79.share.zrok.io',
]
# END CORS CONFIGURATION

# DATABASE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.environ.get('DB_NAME', 'commerce_coordinator'),
        'USER': os.environ.get('DB_USER', 'root'),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST': os.environ.get('DB_HOST', '127.0.0.1'),
        'PORT': os.environ.get('DB_PORT', 3406),
        'ATOMIC_REQUESTS': False,
        'CONN_MAX_AGE': 60,
    }
}
# END DATABASE CONFIGURATION

# EMAIL CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
# END EMAIL CONFIGURATION

# TOOLBAR CONFIGURATION
# See: https://django-debug-toolbar.readthedocs.org/en/latest/installation.html
if os.environ.get('ENABLE_DJANGO_TOOLBAR', False):
    INSTALLED_APPS += (
        'debug_toolbar',
    )

    MIDDLEWARE_CLASSES += (
        'debug_toolbar.middleware.DebugToolbarMiddleware',
    )

    DEBUG_TOOLBAR_PATCH_SETTINGS = False

INTERNAL_IPS = ('127.0.0.1',)
# END TOOLBAR CONFIGURATION

REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'] += (
    'rest_framework.renderers.BrowsableAPIRenderer',
)

# AUTHENTICATION
# Use a non-SSL URL for authorization redirects
SOCIAL_AUTH_REDIRECT_IS_HTTPS = False

# Generic OAuth2 variables irrespective of SSO/backend service key types.
OAUTH2_PROVIDER_URL = 'http://localhost:18000/oauth2'

# OAuth2 variables specific to social-auth/SSO login use case.
SOCIAL_AUTH_EDX_OAUTH2_KEY = os.environ.get('SOCIAL_AUTH_EDX_OAUTH2_KEY', 'commerce-coordinator-sso-key')
SOCIAL_AUTH_EDX_OAUTH2_SECRET = os.environ.get('SOCIAL_AUTH_EDX_OAUTH2_SECRET', 'commerce-coordinator-sso-secret')
SOCIAL_AUTH_EDX_OAUTH2_ISSUER = os.environ.get('SOCIAL_AUTH_EDX_OAUTH2_ISSUER', 'http://localhost:18000')
SOCIAL_AUTH_EDX_OAUTH2_URL_ROOT = os.environ.get('SOCIAL_AUTH_EDX_OAUTH2_URL_ROOT', 'http://localhost:18000')
SOCIAL_AUTH_EDX_OAUTH2_LOGOUT_URL = os.environ.get('SOCIAL_AUTH_EDX_OAUTH2_LOGOUT_URL', 'http://localhost:18000/logout')
SOCIAL_AUTH_EDX_OAUTH2_PUBLIC_URL_ROOT = os.environ.get(
    'SOCIAL_AUTH_EDX_OAUTH2_PUBLIC_URL_ROOT', 'http://localhost:18000',
)

# OAuth2 variables specific to backend service API calls.
BACKEND_SERVICE_EDX_OAUTH2_PROVIDER_URL = os.environ.get(
    'BACKEND_SERVICE_EDX_OAUTH2_PROVIDER_URL',
    'http://localhost:18000'
)
BACKEND_SERVICE_EDX_OAUTH2_KEY = os.environ.get(
    'BACKEND_SERVICE_EDX_OAUTH2_KEY',
    'commerce-coordinator-backend-service-key'
)
BACKEND_SERVICE_EDX_OAUTH2_SECRET = os.environ.get(
    'BACKEND_SERVICE_EDX_OAUTH2_SECRET',
    'commerce-coordinator-backend-service-secret'
)

JWT_AUTH.update({
    'JWT_SECRET_KEY': 'lms-secret',
    'JWT_ISSUER': 'http://localhost:18000/oauth2',
    'JWT_AUDIENCE': None,
    'JWT_VERIFY_AUDIENCE': False,
    'JWT_PUBLIC_SIGNING_JWK_SET': (
        '{"keys": [{"kid": "devstack_key", "e": "AQAB", "kty": "RSA", "n": "smKFSYowG6nNUAdeqH1jQQnH1PmIHphzBmwJ5vRf1vu'
        '48BUI5VcVtUWIPqzRK_LDSlZYh9D0YFL0ZTxIrlb6Tn3Xz7pYvpIAeYuQv3_H5p8tbz7Fb8r63c1828wXPITVTv8f7oxx5W3lFFgpFAyYMmROC'
        '4Ee9qG5T38LFe8_oAuFCEntimWxN9F3P-FJQy43TL7wG54WodgiM0EgzkeLr5K6cDnyckWjTuZbWI-4ffcTgTZsL_Kq1owa_J2ngEfxMCObnzG'
        'y5ZLcTUomo4rZLjghVpq6KZxfS6I1Vz79ZsMVUWEdXOYePCKKsrQG20ogQEkmTf9FT_SouC6jPcHLXw"}]}'
    ),
    'JWT_ISSUERS': [{
        'AUDIENCE': 'lms-key',
        'ISSUER': 'http://localhost:18000/oauth2',
        'SECRET_KEY': 'lms-secret',
    }],
})

ENABLE_AUTO_AUTH = True

LOGGING = get_logger_config(debug=DEBUG)

CELERY_BROKER_URL = "redis://:password@localhost:6379/0"

EDX_API_KEY = 'PUT_YOUR_API_KEY_HERE'  # This is the actual API key in devstack.

# DevStack URLs (Next 3 variables)
# Service List: https://edx.readthedocs.io/projects/open-edx-devstack/en/latest/service_list.html
ECOMMERCE_URL = "http://localhost:18130"

LMS_DASHBOARD_URL = "http://localhost:18000"  # fix me

TITAN_URL = "http://example.com"

TITAN_OAUTH2_PROVIDER_URL = "http://example.com"

FULFILLMENT_TIMEOUT = 15  # Devstack is slow!

PAYMENT_PROCESSOR_CONFIG = {
    'edx': {
        'stripe': {
            'api_version': '2022-08-01; server_side_confirmation_beta=v1',
            'enable_telemetry': None,
            'log_level': 'debug',
            'max_network_retries': 0,
            'proxy': None,
            'publishable_key': 'pk_test_51Ls7QSH4caH7G0X1prLj26IWylx2AP5vGA3nd4GMGPRXjVQlA9HATsF2aC5QhbeGNnTr2xijDLQPQzqefrMvHvke00L5eGLK4N',
            'secret_key': 'sk_test_51Ls7QSH4caH7G0X1EYdtyB8nd9mZxOkpm8qDg4cv2GPVYZkP0tGttGn7DAJgBZMWyxme3Gjro8u6ClqbnDwxcAH9001GSoURRk',
            'source_system_identifier': 'edx/commerce_coordinator?v=1',
            'webhook_endpoint_secret': 'SET-ME-PLEASE',
        },
    },
}

COMMERCETOOLS_MERCHANT_CENTER_ORDERS_PAGE_URL = \
    'https://mc.us-central1.gcp.commercetools.com/2u-marketplace-dev-01/orders'

#####################################################################
# Lastly, see if the developer has any local overrides.
if os.path.isfile(join(dirname(abspath(__file__)), 'private.py')):
    from .private import *  # pylint: disable=import-error
