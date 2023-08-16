"""
Utils for stripe app.
"""


def convert_dollars_in_cents(dollars):
    """
    Convert Dollars amount in cents.
        Arguments:
            dollars (float): dollars amount.
    """
    return int(float(dollars) * 100)


def sanitize_provider_response_body(response_body):
    """
    Remove secrets (e.g: client secret) to make it safe for saving in databases
    """
    if 'client_secret' in response_body:  # remove client secret before saving in titan
        del response_body['client_secret']

    return response_body
