"""
Demo LMS app filter pipeline implementations.
"""

from openedx_filters import PipelineStep


# PipelineSteps augment, filter, or transform data passed into them and return a dict that gets merged into the
# `**kwargs` passed to the next step in the pipeline.  The merge is done using
# [dict.update()](https://docs.python.org/3/library/stdtypes.html#dict.update)
#
# By overriding `run_filter` and adding expected arguments to the signature, we get a small amount checking that the
# name, for example here "sample_data", was among the arguments passed in.
class AddSomeData(PipelineStep):
    """
    Adds data to the sample data list.
    """
    def run_filter(self, sample_data, *args, **kwargs):  # pylint: disable=arguments-differ
        return {
            "sample_data": sample_data + ["A string", {"dict": "like me"}],
        }


class AddSomeMoreData(PipelineStep):
    """
    Adds more data to the sample data list.
    """
    def run_filter(self, sample_data, *args, **kwargs):  # pylint: disable=arguments-differ
        return {
            "sample_data": sample_data + [{"turtles": {"turtles": {"turtles": "all the way down"}}}],
        }
