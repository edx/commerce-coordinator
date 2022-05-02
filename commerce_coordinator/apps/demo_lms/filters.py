"""
Demo LMS app filter definitions.
"""
from openedx_filters.tooling import OpenEdxPublicFilter


# Filter definitions create a filter pipeline; when run, the pipeline works as an extension point to delegate some
# work to other component apps. (In this PoC, though, the steps are implemented in `pipeline.py` rather than another
# app)
class SampleDataRequested(OpenEdxPublicFilter):
    """
    Filter to request sample data
    """
    # This is the key for configuring the pipeline steps in the OPEN_EDX_FILTERS_CONFIG dict in `settings/base.py`
    filter_type = "org.edx.coordinator.demo_lms.sample_data.v1"

    # Although pipelines can be run using the generic `run_pipeline` method, implementing a `run_filter` method allows
    # more control, including a specific signature, default arguments, and extracting the relevant results

    @classmethod
    def run_filter(cls, sample_data=None):
        """
        Execute the filter pipeline with the desired signature.
        """
        if sample_data is None:
            sample_data = []
        data = super().run_pipeline(sample_data=sample_data)
        sample_data = data.get("sample_data")
        return sample_data
