from commerce_coordinator.apps.commercetools.management.commands._ct_api_client_command import (
    CommercetoolsAPIClientCommand,
)
from commerce_coordinator.apps.commercetools.utils import has_refund_transaction


class Command(CommercetoolsAPIClientCommand):
    help = "Find Pending Fulfillment Non Refunded Orders in commercetools"

    def handle(self, *args, **options):
        order_state = "Complete"
        line_item_state_id = "bb686576-3bd5-4457-890a-d63c3d31b2ab"

        # TODO: Change for your use case
        last_modified_at = "2024-10-23T00:00:00"
        limit = 500
        offset = 0

        orders_result = self.ct_api_client.base_client.orders.query(
            where=[
                f'orderState="{order_state}"',
                f'lastModifiedAt>"{last_modified_at}"',
                f'lineItems(state(state(id="{line_item_state_id}")))',
            ],
            sort=["completedAt desc", "lastModifiedAt desc"],
            limit=limit,
            offset=offset,
            expand=["paymentInfo.payments[*]"],
        )

        orders = orders_result.results
        non_refunded_orders = []

        print(f"Total Orders: {orders_result.total}")

        for order in orders:
            if order.payment_info and order.payment_info.payments:
                payments = order.payment_info.payments
                refund_found = False

                for payment_ref in payments:
                    payment = (
                        payment_ref.obj
                    )  # Expand the payment reference to access the payment object
                    refund_found = has_refund_transaction(payment)

                    if refund_found:
                        break

                if not refund_found:
                    non_refunded_orders.append(order)
            else:
                # Orders with no payment info are considered non-refunded
                non_refunded_orders.append(order)

        print(f"Non-Refunded Orders: {len(non_refunded_orders)}")

        for order in non_refunded_orders:
            print(f"Order ID: {order.id}")
