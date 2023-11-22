"""Commercetools pipeline test cases"""
from commerce_coordinator.apps.commercetools.pipeline import GetCommercetoolsOrders
from commerce_coordinator.apps.commercetools.tests._test_cases import MonkeyPatchedGetOrderTestCase
from commerce_coordinator.apps.core.constants import ORDER_HISTORY_PER_SYSTEM_REQ_LIMIT


class PipelineTests(MonkeyPatchedGetOrderTestCase):
    """Commercetools pipeline testcase"""

    def test_pipeline(self):
        """Ensure pipeline is functioning as expected"""

        pipe = GetCommercetoolsOrders("test_pipe", None)
        ret = pipe.run_filter(
            {
                "edx_lms_user_id": 127,
                "page_size": ORDER_HISTORY_PER_SYSTEM_REQ_LIMIT,
                "page": 0,
            },
            []
        )

        self.assertEqual(len(ret['order_data']), len(self.orders))
