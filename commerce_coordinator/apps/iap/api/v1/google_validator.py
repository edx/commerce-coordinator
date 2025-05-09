import logging
from inapppy import GooglePlayVerifier, errors

logger = logging.getLogger(__name__)

class GooglePlayValidator:
    def validate(self, purchase_token: str, product_sku: str, configuration: dict) -> dict:
        """
        Validates the purchase token with Google Play.

        Args:
            purchase_token (str): The purchase token provided by the client.
            product_sku (str): The product SKU for the purchase.
            configuration (dict): Configuration dictionary for Google Play.

        Returns:
            dict: Validation response with raw response and status flags.
        """
        # bundle_id = configuration.get('google_bundle_id')
        # google_service_account_key_file = configuration.get('google_service_account_key_file')
        bundle_id = "com.example.myapp"
        google_service_account_key_file = {
            "type": "service_account",
            "project_id": "your-google-project-id",
            "private_key_id": "your-private-key-id",
            "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADAN...valid_base64_data...QAB\n-----END PRIVATE KEY-----\n",
            "client_email": "your-service-account@your-google-project.iam.gserviceaccount.com",
            "client_id": "123456789012345678901",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/your-service-account%40your-google-project.iam.gserviceaccount.com"
        }
        if not bundle_id or not google_service_account_key_file:
            logger.error("Google Play configuration missing 'google_bundle_id' or 'google_service_account_key_file'.")
            return {'error': 'Invalid Google Play configuration.'}

        try:
            verifier = GooglePlayVerifier(bundle_id, google_service_account_key_file)
            response = verifier.verify_with_result(
                purchase_token,
                product_sku,
                is_subscription=False
            )

            return {
                'raw_response': response.raw_response,
                'is_canceled': response.is_canceled,
                'is_expired': response.is_expired
            }
        except errors.GoogleError as exc:
            logger.error('Google Play validation failed: %s', exc)
            return {
                'error': str(exc),
                'message': exc.message if hasattr(exc, 'message') else 'Unknown error occurred'
            }
