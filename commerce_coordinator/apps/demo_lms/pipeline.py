

from openedx_filters import PipelineStep


class SomeData(PipelineStep):
    """
    Adds data to the sample data list.
    """
    def run_filter(self, sample_data, *args, **kwargs):  # pylint: disable=arguments-differ
        return {
            "sample_data": sample_data + ["A string", {"dict": "like me"}],
        }


class SomeMoreData(PipelineStep):
    """
    Adds data to the sample data list.
    """
    def run_filter(self, sample_data, *args, **kwargs):  # pylint: disable=arguments-differ
        return {
            "sample_data": sample_data + [{"turtles": {"turtles": {"turtles": "all the way down"}}}],
        }
