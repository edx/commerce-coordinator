from commerce_coordinator.settings.local import *

# Use edx.devstack.mysql for database.
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.environ.get('DB_NAME', 'commerce-coordinator'),
        'USER': os.environ.get('DB_USER', 'root'),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST': os.environ.get('DB_HOST', 'commerce-coordinator.db'),
        'PORT': os.environ.get('DB_PORT', 3306),
        'ATOMIC_REQUESTS': False,
        'CONN_MAX_AGE': 60,
    }
}

# Wire internal OAuth2 URLs to use internal devstack networking.
OAUTH2_PROVIDER_URL = 'http://edx.devstack.lms:18000/oauth2'
SOCIAL_AUTH_EDX_OAUTH2_URL_ROOT = os.environ.get('SOCIAL_AUTH_EDX_OAUTH2_URL_ROOT', 'http://edx.devstack.lms:18000')

# Use edx.devstack.redis for queue.
CELERY_BROKER_URL = "redis://:password@edx.devstack.redis:6379/0"

# Application URLs in devstack.
ECOMMERCE_URL = "http://edx.devstack.ecommerce:18130"
TITAN_URL = os.environ.get('TITAN_URL_ROOT', 'http://titan_titan-app_1:3000')
