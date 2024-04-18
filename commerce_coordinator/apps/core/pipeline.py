"""
Core pipeline steps, Usually Utilities
"""

from openedx_filters import PipelineStep

from commerce_coordinator.apps.core.constants import PipelineCommand


# pylint: disable=forgotten-debug-statement, unused-argument
class DebugPipeline(PipelineStep):
    """
    Debug pipeline step
    """

    def run_filter(self, **params):
        """
        Debug pipeline step
        """

        breakpoint()

        return PipelineCommand.CONTINUE.value
