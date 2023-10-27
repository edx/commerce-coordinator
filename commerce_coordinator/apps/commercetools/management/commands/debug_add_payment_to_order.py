import json

from commercetools.platform.models import (
    CustomerResourceIdentifier,
    OrderAddPaymentAction,
    PaymentDraft,
    PaymentMethodInfo,
    PaymentResourceIdentifier,
    PaymentStatusDraft,
    TransactionDraft,
    TransactionType,
    TypedMoney
)
from django.core.management.base import no_translations

from commerce_coordinator.apps.commercetools.catalog_info.utils import ls
from commerce_coordinator.apps.commercetools.management.commands._ct_api_client_command import (
    CommercetoolsAPIClientCommand
)


class Command(CommercetoolsAPIClientCommand):
    help = "Insert or Update the base 2U Customer Custom Type Object"

    # Django Overrides
    # Django Overrides
    def add_arguments(self, parser):
        parser.add_argument("order_uuid", nargs='?', type=str)

    @no_translations
    def handle(self, *args, **options):
        order_uuid = options['order_uuid']
        current_order = self.ct_api_client.base_client.orders.get_by_id(order_uuid)

        money = TypedMoney.deserialize(current_order.total_price.serialize())

        # Comments are MC UI Name on order Payments Screen.
        # There is an open question on how to store last 4 digits of credit/debit cards.
        payment = self.ct_api_client.base_client.payments.create(PaymentDraft(
            customer=CustomerResourceIdentifier(id=current_order.customer_id),
            interface_id="Stripe",                      # Payment provider ID
            amount_authorized=money,
            amount_paid=money,
            amount_planned=money,                       # Amount planned
            payment_method_info=PaymentMethodInfo(
                payment_interface="Stripe",             # Payment service provider (PSP)
                method="credit card",                   # Payment method
                name=ls({'en': 'Mastercard'})           # Payment method name
            ),
            payment_status=PaymentStatusDraft(
                interface_code="completed",             # PSP Status Code
                interface_text="Completed",             # Description
            ),
            transactions=[                              # Payment transactions (table)
                TransactionDraft(
                    type=TransactionType.CHARGE,            # Transaction type
                    amount=money                            # Amount
                )
            ],
        ))

        ret = self.ct_api_client.base_client.orders.update_by_id(order_uuid, current_order.version, actions=[
            OrderAddPaymentAction(payment=PaymentResourceIdentifier(id=payment.id))
        ])

        print(json.dumps(ret.serialize(), indent=2))
