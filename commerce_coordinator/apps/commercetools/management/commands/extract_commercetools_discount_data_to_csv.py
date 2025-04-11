from datetime import datetime
import csv
from enum import Enum
from itertools import product
from typing import List

from commercetools.platform.models import DiscountCode

from commerce_coordinator.apps.commercetools.management.commands._ct_api_client_command import (
    CommercetoolsAPIClientCommand
)


# Enum for product types
class ProductType(Enum):
    EDX_COURSE_ENTITLEMENT = "edx_course_entitlement"
    EDX_PROGRAM = "edx_program"
    OC_SELF_PACED = "oc_self_paced"
    EDX_COURSE = "oc_self_paced"

STAGE_PRODUCT_TYPE_ID_MAPPING = {
    ProductType.EDX_COURSE_ENTITLEMENT.value: "12e5510c-a4d6-4301-9caf-17053e57ff71",
    ProductType.EDX_PROGRAM.value: "79fb6abe-8373-4dec-a8d1-51242b1798b8",
    ProductType.OC_SELF_PACED.value: "9f8ec882-043a-4225-8811-00ac5acfd580"
}

PROD_PRODUCT_TYPE_ID_MAPPING = {
    ProductType.EDX_COURSE_ENTITLEMENT.value: "9f1f189a-4d79-4eaa-9c6e-cfcb61aa779f",
    ProductType.EDX_PROGRAM.value: "c6a2d629-a50e-4d88-bd01-ab05a0617eae",
    ProductType.EDX_COURSE.value: "b241ac79-fee2-461d-b714-8f3c4a1c4c0e"
}

class Command(CommercetoolsAPIClientCommand):
    help = "Fetch and verify course attributes from CommerceTools"

    def handle(self, *args, **options):
        # Fetch discounts based on type
        discounts = self.fetch_discounts()

        # Write data to CSV
        self.write_attributes_to_csv(discounts)

    def fetch_discounts(self):
        page_size = 1

        lastId = None
        should_continue = True
        results = []
        while should_continue:
            if lastId is None:
                response = self.ct_api_client.base_client.discount_codes.query(
                limit=page_size,
                sort="id asc",
                expand="cartDiscounts[*]",
            )
            else:
                response =  self.ct_api_client.base_client.discount_codes.query(
                limit=page_size,
                sort="id asc",
                expand="cartDiscounts[*]",
                where=f'id > "{lastId}"'
            )
            if not response:
                print("Failed to get discount codes with code from Commercetools.")
                return None


            batch_results = response.results
            results.extend(batch_results)
            should_continue = (len(batch_results) == page_size)
            if batch_results:
                lastId = batch_results[-1].id

        return results

    def write_attributes_to_csv(self, discounts: List[DiscountCode]):
        if not discounts:
            print(f"No discounts found.")
            return

        # Dynamically extract all unique keys across all product dictionaries

        discounts_new = []
        for discount in discounts:
            cart_discount = discount.cart_discounts[0].obj
            discount = {
                "name": discount.name.get('en-US', ''),
                "code": discount.code,
                "validFrom": discount.valid_from,
                "validUntil": discount.valid_until,
                "maxApplications": discount.max_applications,
                "cartDiscountName": cart_discount.name.get('en-US', ''),
                "cartDiscountKey": cart_discount.key,
                "discountType": cart_discount.custom.fields.get('discountType'),
                "category": cart_discount.custom.fields.get('category'),
                "channel": cart_discount.custom.fields.get('channel'),
            }
            discounts_new.append(discount)


        # Define CSV filename with product type and date
        filename = f"discount_{datetime.now().strftime('%Y%m%d')}.csv"

        # Write to CSV
        with open(filename, "w", newline="") as output_file:
            dict_writer = csv.DictWriter(output_file, fieldnames=discounts_new[0].keys())
            dict_writer.writeheader()
            dict_writer.writerows(discounts_new)

        print(f"\n\n\n\n\n\n\nCSV file '{filename}' written successfully with {len(discounts)} records.")
