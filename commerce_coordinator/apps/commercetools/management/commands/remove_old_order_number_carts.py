from commercetools import CommercetoolsError

from commerce_coordinator.apps.commercetools.management.commands._ct_api_client_command import (
    CommercetoolsAPIClientCommand
)


class Command(CommercetoolsAPIClientCommand):
    help = "Remove old order number carts from commercetools"

    def handle(self, *args, **options):
        # Query parameters for old order number carts
        where_clause = [
            'createdAt<"2024-08-07"',
            'cartState="Active"',
            "paymentInfo is not defined",
        ]

        limit = 500
        offset = 0
        deleted_count = 0
        batch_number = 0

        print("Starting to remove old order number carts...")

        # Process all carts in batches
        while True:
            batch_number += 1
            response = self.ct_api_client.base_client.carts.query(
                where=where_clause,
                limit=limit,
                offset=offset,
            )
            carts = response.results
            if not carts:
                break

            print(
                f"Found {response.results}/{response.total} carts to delete "
                f"in batch {batch_number}"
            )

            orders = ",".join(
                [
                    f'"{cart.custom.fields.get("orderNumber")}"'
                    for cart in carts
                    if cart.custom
                ]
            )
            orders = self.ct_api_client.base_client.orders.query(
                where=[f"orderNumber in ({orders})"],
                limit=limit,
            )
            orders = {order.order_number for order in orders.results}

            deleted_count_in_loop = 0
            for cart in carts:
                try:
                    order_number = (
                        cart.custom.fields.get("orderNumber")
                        if cart.custom
                        else None
                    )
                    if order_number in orders:
                        print(
                            f"Skipping cart {cart.id} with existing order "
                            f"number: {order_number}"
                        )
                        continue
                    if (
                        not order_number
                        or not order_number.startswith("2U-")
                        or len(order_number) != 9
                    ):
                        print(
                            f"Skipping cart {cart.id} with unexpected "
                            f"order number: {order_number}"
                        )
                        continue
                    self.ct_api_client.base_client.carts.delete_by_id(
                        cart.id, version=cart.version
                    )
                    deleted_count_in_loop += 1
                    print(
                        f"Deleted cart {cart.id} (v{cart.version}) with "
                        f"order number {order_number} of customer {cart.customer_email}"
                    )
                except CommercetoolsError as e:
                    print(f"Failed to delete cart {cart.id}: {str(e)}")

            deleted_count += deleted_count_in_loop
            if deleted_count_in_loop == 0:
                print("No carts to delete in this batch, moving to next batch...")
                offset += limit

        print(f"Successfully deleted {deleted_count} old order number carts")
