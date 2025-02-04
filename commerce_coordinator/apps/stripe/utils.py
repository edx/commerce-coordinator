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
