"""FAEcomm Test configuration/utility functions"""
import json
import os
import pathlib
from typing import Any, Dict, Union

from commercetools.platform.models import Order as CTOrder
from stripe import PaymentIntent


def gen_order_for_payment_intent() -> CTOrder:
    """Generate CT Order attached to canned Payment intent with Charges for Full Testing"""
    file_path = os.path.join(pathlib.Path(__file__).parent.resolve(), 'raw_ct_order_with_stripe_paymentintent.json')
    with open(file_path) as f:
        obj = json.load(f)
        return CTOrder.deserialize(obj)


def gen_payment_intent(hydrate=True) -> Union[PaymentIntent, Dict[str, Any]]:
    """Generate payment intent with Charges for Full Testing"""
    with open(os.path.join(pathlib.Path(__file__).parent.resolve(), 'raw_stripe_paymentintent_with_charges.json')) as f:
        obj = json.load(f)

        if not hydrate:  # pragma no cover
            return obj

        intent = PaymentIntent()
        intent.refresh_from(obj)
        return intent
