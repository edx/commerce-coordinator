import json
from collections import defaultdict

from commerce_coordinator.apps.commercetools.management.commands._ct_api_client_command import (
    CommercetoolsAPIClientCommand
)

""" Those intending to use this script, please take into consideration that currently
the script doesn't cater for the returns (refunds) and hence
it will show the duplicates even if the user has returned the product.
 """


class Command(CommercetoolsAPIClientCommand):
    help = "Find duplicate purchases in commercetools"

    def handle(self, *args, **options):

        order_state = "Complete"
        # TODO: Change for your use case
        last_modified_at = "2024-10-23T00:00:00"

        orders_result = self.ct_api_client.base_client.orders.query(
            where=[
                f'orderState="{order_state}"',
                f'lastModifiedAt>"{last_modified_at}"',
            ],
            sort=["completedAt desc", "lastModifiedAt desc"],
            limit=500,
            offset=0,
        )

        orders = orders_result.results

        while orders_result.offset + orders_result.limit < orders_result.total:
            orders_result = self.ct_api_client.base_client.orders.query(
                where=[
                    f'orderState="{order_state}"',
                    'lastModifiedAt>"2024-10-23T00:00:00"',
                ],
                sort=["completedAt desc", "lastModifiedAt desc"],
                limit=orders_result.limit,
                offset=orders_result.offset + orders_result.limit,
            )
            orders.extend(orders_result.results)

        user_orders = defaultdict(lambda: defaultdict(list))

        for order in orders:
            user_email = order.customer_email
            line_items = order.line_items

            for item in line_items:
                sku = item.variant.sku
                user_orders[user_email][sku].append(order.id)

        duplicate_purchases = {}
        for user_id, sku_orders in user_orders.items():
            duplicates = {
                sku: order_ids
                for sku, order_ids in sku_orders.items()
                if len(order_ids) > 1
            }
            if duplicates:
                duplicate_purchases[user_id] = duplicates

        # dump to a json file
        with open("duplicate_purchases.json", "w") as f:
            json.dump(duplicate_purchases, f)
