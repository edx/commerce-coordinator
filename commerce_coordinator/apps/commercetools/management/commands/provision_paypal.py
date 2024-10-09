import json

import requests
from commercetools import CommercetoolsError
from commercetools.platform.models import (
    StateChangeInitialAction,
    StateResourceIdentifier,
    StateSetDescriptionAction,
    StateSetNameAction,
    StateSetTransitionsAction,
    CustomObjectDraft,
    TypeDraft,
    CustomFieldEnumType,
    FieldDefinition
)
from django.core.management.base import no_translations

from commerce_coordinator.apps.commercetools.catalog_info.foundational_types import (
    TwoUCustomStates,
)
from commerce_coordinator.apps.commercetools.catalog_info.utils import ls_eq
from commerce_coordinator.apps.commercetools.management.commands._ct_api_client_command import (
    CommercetoolsAPIClientCommand,
)


class Command(CommercetoolsAPIClientCommand):
    help = "Add PayPal Custom Object, Type and Custom Fields"

    @no_translations
    def handle(self, *args, **options):
        data = CustomObjectDraft(
            container="paypal-commercetools-connector",
            key="settings",
            version=1,
            value={
                "merchantId": "",  # string
                "email": "test@example.com",  # string
                "acceptPayPal": True,  # boolean
                "acceptPayLater": False,  # boolean
                "acceptVenmo": False,  # boolean
                "acceptLocal": False,  # boolean
                "acceptCredit": False,  # boolean
                "buttonPaymentPage": False,  # boolean
                "buttonCartPage": False,  # boolean
                "buttonDetailPage": False,  # boolean
                "buttonShippingPage": False,  # boolean
                "buttonShape": "pill",  # "rect" | "pill"
                "buttonTagline": False,  # boolean
                "payLaterMessagingType": {},  # Record<string, "flex" | "text">
                "payLaterMessageHomePage": False,  # boolean
                "payLaterMessageCategoryPage": False,  # boolean
                "payLaterMessageDetailsPage": False,  # boolean
                "payLaterMessageCartPage": False,  # boolean
                "payLaterMessagePaymentPage": False,  # boolean
                "payLaterMessageTextLogoType": "none",  # "inline" | "primary" | "alternative" | "none"
                "payLaterMessageTextLogoPosition": "left",  # "left" | "right" | "top"
                "payLaterMessageTextColor": "black",  # "black" | "white" | "monochrome" | "grayscale"
                "payLaterMessageTextSize": "10",  # "10" | "11" | "12" | "13" | "14" | "15" | "16"
                "payLaterMessageTextAlign": "left",  # "left" | "center" | "right"
                "payLaterMessageFlexColor": "blue",  # "blue" | "black" | "white" | "white-no-border" | "gray" | "monochrome" | "grayscale"
                "payLaterMessageFlexRatio": "1x1",  # "1x1" | "1x4" | "8x1" | "20x1"
                "threeDSOption": "",  # "" | "SCA_ALWAYS" | "SCA_WHEN_REQUIRED"
                "payPalIntent": "Capture",  # "Authorize" | "Capture"
                "ratePayBrandName": {},  # CustomDataStringObject
                "ratePayLogoUrl": {},  # CustomDataStringObject
                "ratePayCustomerServiceInstructions": {},  # CustomDataStringObject
                "paymentDescription": {},  # CustomDataStringObject
                "storeInVaultOnSuccess": False,  # boolean
                "paypalButtonConfig": {  # PayPal button configuration
                    "buttonColor": "blue",  # "gold" | "blue" | "white" | "silver" | "black"
                    "buttonLabel": "buynow",  # "paypal" | "checkout" | "buynow" | "pay" | "installment"
                },
                "hostedFieldsPayButtonClasses": "",  # string
                "hostedFieldsInputFieldClasses": "",  # string
                "threeDSAction": {},  # Record<string, any>
            }

        )

        try:
            custom_object = self.ct_api_client.base_client.custom_objects.create(draft=data)

#             custom_type = self.ct_api_client.base_client.types.create(TypeDraft(
#                  key='paypaltype'
#                  name=ls({'en': 'PayPal Payment Type'}),
#                  description=ls({'en': 'Custom Type for PayPal Payment'}),
#                  field_definitions= [
#                      FieldDefinition(
#                         name="
#                      )
#                      )
# #                      fieldDefinitions" : [ {
# #     "name" : "offer_name",
# #     "label" : {
# #       "en" : "offer_name"
# #     },
# #     "required" : false,
# #     "type" : {
# #       "name" : "String"
# #     },
# #     "inputHint" : "SingleLine"
# #   } ]
#                  ]


#             ))
        except CommercetoolsError as _:  # pragma: no cover
            # commercetools.exceptions.CommercetoolsError: The Resource with key '' was not found.
            pass
        except (
            requests.exceptions.HTTPError
        ) as _:  # The test framework doesn't wrap to CommercetoolsError
            pass

        print(json.dumps(custom_object.serialize()))
