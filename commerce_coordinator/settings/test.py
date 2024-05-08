import os

from commerce_coordinator.settings.base import *

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
            'webhook_endpoint_secret': 'SET-ME-PLEASE',
        },
    },
}
# END PAYMENT PROCESSING

# IN-MEMORY TEST DATABASE
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    },
}
# END IN-MEMORY TEST DATABASE

# CACHE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#caches
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

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
    # Actual Production Signals
    'commerce_coordinator.apps.ecommerce.signals.enrollment_code_redemption_requested_signal': [
        'commerce_coordinator.apps.titan.signals.enrollment_code_redemption_requested_create_order',
    ],
    'commerce_coordinator.apps.titan.signals.fulfill_order_placed_signal': [
        'commerce_coordinator.apps.lms.signal_handlers.fulfill_order_placed_send_enroll_in_course',
    ],
    'commerce_coordinator.apps.ecommerce.signals.order_created_signal': [
        'commerce_coordinator.apps.titan.signals.order_created_save',
    ],
    'commerce_coordinator.apps.stripe.signals.payment_processed_signal': [
        'commerce_coordinator.apps.titan.signals.payment_processed_save',
    ],
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
}

COMMERCETOOLS_CONFIG = {
    # These values have special meaning to the CT SDK Unit Testing, and will fail if changed.
    'clientId': "mock-client-id",
    'clientSecret': "mock-client-secret",
    'scopes': "manage_project:test",
    'apiUrl': "https://localhost",
    'authUrl': "https://localhost/oauth/token",
    'projectKey': "test",
}
