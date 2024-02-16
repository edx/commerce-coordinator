import json
import os
import pathlib

from stripe import PaymentIntent


def gen_payment_intent() -> PaymentIntent:
    """Generate payment intent with Charges for Full Testing"""
    with open(os.path.join(pathlib.Path(__file__).parent.resolve(), 'raw_stripe_paymentintent_with_charges.json')) as f:
        obj = json.load(f)
        intent = PaymentIntent()
        intent.refresh_from(obj)
        return intent
