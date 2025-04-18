import csv
from datetime import datetime
from typing import Dict, List

from commerce_coordinator.apps.commercetools.http_api_client import CTCustomAPIClient
from commerce_coordinator.apps.commercetools.management.commands._timed_command import TimedCommand


class Command(TimedCommand):
    help = "Fetch and verify discount attributes from CommerceTools"

    def handle(self, *args, **options):
        try:
            ct_api_client = CTCustomAPIClient()
        except Exception as e:
            print(f"Error initializing Commercetools API client: {e}")
            return

        # Fetch discounts based on type
        discounts = self.fetch_discounts(ct_api_client)

        # Write data to CSV
        self.write_attributes_to_csv(discounts)

    def fetch_discounts(self, ct_api_client):
        page_size = 500

        lastId = None
        should_continue = True
        results = []
        while should_continue:
            if lastId is None:
                response = ct_api_client._make_request(
                    method="GET",
                    endpoint="discount-codes",
                    params={
                        "limit": page_size,
                        "sort": "id asc",
                        "expand": "cartDiscounts[*]",
                    }
                )
            else:
                response = ct_api_client._make_request(
                    method="GET",
                    endpoint="discount-codes",
                    params={
                        "limit": page_size,
                        "sort": "id asc",
                        "expand": "cartDiscounts[*]",
                        "where": f'id > "{lastId}"'
                    }
                )
            if not response:
                print("Failed to get discount codes with code from Commercetools.")
                return None

            batch_results = response["results"]
            results.extend(batch_results)
            should_continue = (len(batch_results) == page_size)

            if batch_results:
                lastId = batch_results[-1]["id"]

        return results

    def write_attributes_to_csv(self, discounts: List[Dict]):
        if not discounts:
            print(f"No discounts found.")
            return

        # Dynamically extract all unique keys across all discount dictionaries
        discounts_new = []
        for discount in discounts:
            cart_discount = discount["cartDiscounts"][0]["obj"]
            discount = {
                "name": discount["name"].get('en-US', ''),
                "code": discount["code"],
                "validFrom": discount.get("validFrom", None),
                "validUntil": discount.get("validUntil", None),
                "maxApplications": discount.get("maxApplications", None),
                "maxApplicationsPerCustomer": discount.get("maxApplicationsPerCustomer", None),
                "cartDiscountName": cart_discount["name"].get('en-US', ''),
                "cartDiscountKey": cart_discount["key"],
                "discountType": cart_discount["custom"]["fields"].get('discountType'),
                "category": cart_discount["custom"]["fields"].get('category'),
                "channel": cart_discount["custom"]["fields"].get('channel'),
            }
            discounts_new.append(discount)

        # Define CSV filename with discount type and date
        filename = f"discount_{datetime.now().strftime('%Y%m%d')}.csv"

        # Write to CSV
        with open(filename, "w", newline="") as output_file:
            dict_writer = csv.DictWriter(output_file, fieldnames=discounts_new[0].keys())
            dict_writer.writeheader()
            dict_writer.writerows(discounts_new)

        print(f"\n\n\n\n\n\n\nCSV file '{filename}' written successfully with {len(discounts_new)} records.")
