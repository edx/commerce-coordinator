"""
App configuration for the Commerce Coordinator Core app.

Among other things, performs the actual mapping of Commerce Coordinator signals and handlers as defined in settings.
"""

import importlib
import logging

from django.apps import AppConfig
from django.conf import ImproperlyConfigured, settings
from segment import analytics

from commerce_coordinator.apps.core.signal_helpers import CoordinatorSignal

logger = logging.getLogger(__name__)


def _get_function_from_string_path(string_path):
    """
    Return a reference to a function from a given string representing a Python dotted path

    For example: "commerce_coordinator.apps.core.foo" would return the foo function.
    """
    package_path, function_name = string_path.rsplit('.', 1)
    package = importlib.import_module(package_path)
    return getattr(package, function_name)


class CoreConfig(AppConfig):
    """
    Django AppConfig object for the core app
    """
    name = 'commerce_coordinator.apps.core'

    def ready(self):
        """
        On Django startup this method will be called once. We perform our signal mapping and configuration checks
        here since the core app will always be installed, and this is the safest place to ensure this code only
        gets run once.

        On app startup:
        - Confirm that every configured signal and handler exists
        - Confirm that no handlers have been connected to the signals by other means
        - Confirm that every signal has at least one handler
        - Hook up handlers to signals
        - Sets the Segment's write key
        """
        for signal_path, receivers in settings.CC_SIGNALS.items():
            signal = _get_function_from_string_path(signal_path)

            if not isinstance(signal, CoordinatorSignal):
                raise ImproperlyConfigured(f'Signal {signal_path} configured in settings.CC_SIGNALS is not an '
                                           f'instance of CoordinatorSignal, this is not allowed.')

            if signal.receivers:
                raise ImproperlyConfigured(f'Signal {signal_path} has previously configured handlers. Commerce '
                                           f'Coordinator receivers must *only* be configured in settings.CC_SIGNALS')

            if not receivers:
                raise ImproperlyConfigured(f'Signal {signal_path} has no registered receivers. Either remove the'
                                           f'signal or add receivers in settings.CC_SIGNALS')

            for handler_path in receivers:
                logger.info(f"Connecting {handler_path} to {signal_path}")
                handler = _get_function_from_string_path(handler_path)
                signal.connect(handler)

        if settings.SEGMENT_KEY:
            analytics.write_key = settings.SEGMENT_KEY
