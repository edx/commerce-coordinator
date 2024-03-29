import json
from datetime import date, datetime

import attr
from django.core.management.base import no_translations

from commerce_coordinator.apps.commercetools.data import order_from_commercetools
from commerce_coordinator.apps.commercetools.management.commands._ct_api_client_command import (
    CommercetoolsAPIClientCommand
)
from commerce_coordinator.apps.core.constants import ORDER_HISTORY_PER_SYSTEM_REQ_LIMIT

MAX_RESULTS = ORDER_HISTORY_PER_SYSTEM_REQ_LIMIT


def json_serialize(obj):
    """ Certain types cant serialize, lets manually handle the ones we find here. """
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    return obj


class Command(CommercetoolsAPIClientCommand):
    help = "Get Order History from Commercetools by LMS User ID"

    # Django Overrides
    def add_arguments(self, parser):
        parser.add_argument("edx_lms_user_id", nargs='?', type=int)
        parser.add_argument("--offset", nargs='?', type=int, default=0)

    @no_translations
    def handle(self, *args, **options):
        edx_lms_user_id = options['edx_lms_user_id']

        offset = options['offset']
        tup = self.ct_api_client.get_orders_for_customer(
            edx_lms_user_id=edx_lms_user_id,
            limit=MAX_RESULTS + 1,
            offset=offset
        )

        ret = tup[0]

        orders = [order_from_commercetools(x, tup[1]) for x in ret.results]

        if len(orders) > MAX_RESULTS:
            orders.pop()  # +1 not needed

        print(json.dumps(
            [attr.asdict(x) for x in orders],
            indent=2,
            default=json_serialize
        ))

        if ret.total <= MAX_RESULTS:
            print("No More Results Available")
        else:
            print(f"There are more results, paginating at {MAX_RESULTS}, current offset: {offset}")
