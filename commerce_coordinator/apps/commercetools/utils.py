"""
Helpers for the commercetools app.
"""

from braze.client import BrazeClient
from django.conf import settings


def get_braze_client():
    """ Returns a Braze client. """
    braze_api_key = settings.BRAZE_API_KEY
    braze_api_url = settings.BRAZE_API_SERVER

    if not braze_api_key or not braze_api_url:
        return None

    return BrazeClient(
        api_key=braze_api_key,
        api_url=braze_api_url,
        app_id='',
    )
