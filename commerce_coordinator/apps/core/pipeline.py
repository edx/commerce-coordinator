from openedx_filters import PipelineStep

from commerce_coordinator.apps.core.constants import PipelineCommand


class HaltIfRedirectUrlProvided(PipelineStep):
    """ A basic pipeline step that will stop if there is a redirect url set."""
    def run_filter(self, redirect_url, **kwargs):
        if redirect_url is not None:
            return PipelineCommand.HALT.value
        return PipelineCommand.CONTINUE.value
