
from openedx_filters.tooling import OpenEdxPublicFilter

class SampleDataRequested(OpenEdxPublicFilter):
    """
    Filter to request sample data, 
    """


    filter_type = "org.edx.coordinator.demo_lms.sample_data.v1"


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
