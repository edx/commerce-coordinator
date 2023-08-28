"""
Filters used by the frontend_app_payment app
"""
import logging

from openedx_filters.tooling import OpenEdxPublicFilter

from commerce_coordinator.apps.frontend_app_payment.serializers import DraftPaymentCreateViewOutputSerializer

logger = logging.getLogger(__name__)


class PaymentRequested(OpenEdxPublicFilter):
    """
    Filter to gather payment data from the defined PipelineStep(s)
    """
    # See pipeline step configuration OPEN_EDX_FILTERS_CONFIG dict in `settings/base.py`
    filter_type = "org.edx.coordinator.frontend_app_payment.payment.get.requested.v1"

    @classmethod
    def run_filter(cls, **kwargs):
        """
        Call the PipelineStep(s) defined for this filter, to gather orders and return together
        Arguments:
            kwargs (dict): Arguments passed through from the original get payment url querystring
        """
        payment = super().run_pipeline(**kwargs)['payment_data']
        return payment


class DraftPaymentRequested(OpenEdxPublicFilter):
    """
    Filter to gather draft payment from the defined PipelineStep(s)
    """
    # See pipeline step configuration OPEN_EDX_FILTERS_CONFIG dict in `settings/base.py`
    filter_type = "org.edx.coordinator.frontend_app_payment.payment.draft.requested.v1"

    @classmethod
    def run_filter(cls, **kwargs):
        """
        Call the PipelineStep(s) defined for this filter, to gather payment draft payment details.
        Arguments:
            kwargs (dict): Arguments passed through from the original get payment url querystring
        """
        pipeline_output = super().run_pipeline(
            edx_lms_user_id=kwargs['edx_lms_user_id'],
        )

        payment_data = pipeline_output.get('payment_data')

        payment_data['order_id'] = payment_data.pop('order_uuid')

        payment_output = DraftPaymentCreateViewOutputSerializer(data={'capture_context': payment_data})
        payment_output.is_valid(raise_exception=True)
        return payment_output.data


class ActiveOrderRequested(OpenEdxPublicFilter):
    """
    Filter to gather payment data from the defined PipelineStep(s)
    """

    filter_type = "org.edx.coordinator.frontend_app_payment.active.order.requested.v1"

    @classmethod
    def run_filter(cls, params):
        """
        Call the PipelineStep(s) defined for this filter, to gather the current order
        Arguments:
            params: arguments passed through from the original get active order url querystring
        """
        pipeline_output = super().run_pipeline(
            edx_lms_user_id=params['edx_lms_user_id'],
        )
        active_order = pipeline_output.get('order_data')
        # TODO: Do we still need this waffle flag? Normally from ecommerce
        # and was used from cybersource to stripe migration.
        active_order['enable_stripe_payment_processor'] = True
        return active_order


class PaymentProcessingRequested(OpenEdxPublicFilter):
    """
    Filter pipeline results for marking the current payment as ready for processing.
    """

    filter_type = "org.edx.coordinator.frontend_app_payment.payment.processing.requested.v1"

    @classmethod
    def run_filter(cls, **kwargs):
        """
        Call the PipelineStep(s) defined for this filter
        Arguments:
            kwargs: arguments passed through from the payment process.
        """
        pipeline_output = super().run_pipeline(
            **kwargs,
        )
        return pipeline_output
