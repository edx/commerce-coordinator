import logging
from inapppy import AppStoreValidator, InAppPyValidationError

logger = logging.getLogger(__name__)

class IOSValidator:
    def validate(self, receipt):  # pylint: disable=unused-argument
        """
        Accepts receipt, validates that the purchase has already been completed in
        Apple for the mentioned product_id.
        """
        # bundle_id = configuration.get('ios_bundle_id')
        bundle_id = "com.example.myapp"

        # auto_retry_wrong_env_request = True automatically queries sandbox if validation fails on production
        validator = AppStoreValidator(bundle_id, auto_retry_wrong_env_request=True)

        try:
            validation_result = validator.validate(
                receipt.get('purchase_token'),
                exclude_old_transactions=True  # if True, include only the latest renewal transaction
            )
        except InAppPyValidationError as ex:
            # handle validation error
            logger.error('Purchase validation failed %s', ex.raw_response)
            return {'error': ex.raw_response}

        logger.info("iOS IAP validated successfully.")
        return validation_result
