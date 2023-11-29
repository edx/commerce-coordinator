import django.conf

from commerce_coordinator.apps.commercetools.clients import CommercetoolsAPIClient
from commerce_coordinator.apps.commercetools.management.commands._timed_command import TimedCommand


class CommercetoolsAPIClientCommand(TimedCommand):
    """A Command Base class for Commercetools API Client Commands"""

    ct_api_client = None

    def __init__(self, stdout=None, stderr=None, no_color=False, force_color=False):
        super().__init__(stdout, stderr, no_color, force_color)

        config = django.conf.settings.COMMERCETOOLS_CONFIG

        print(f'Using commercetools API config: {config["projectKey"]} / {config["importUrl"]}')

        self.ct_api_client = CommercetoolsAPIClient()
