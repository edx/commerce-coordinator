import csv
from datetime import datetime
from time import sleep

import django.conf

from commerce_coordinator.apps.commercetools.http_api_client import CTCustomAPIClient
from commerce_coordinator.apps.commercetools.management.commands._timed_command import TimedCommand


class Command(TimedCommand):
    HISTORY_API_URL = "https://history.us-central1.gcp.commercetools.com/"
    DEFAULT_COOLDOWN = 5
    RETRY_COOLDOWN = 30
    """Command to get Commercetools audit history."""

    def handle(self, *args, **options):
        """Handle the command."""
        config = django.conf.settings.COMMERCETOOLS_CONFIG
        client = CTCustomAPIClient()
        results = []

        while True:
            print("Fetching page #", (len(results)) // 20 + 1)
            response = client._make_request(
                method="GET",
                endpoint="",
                base_backoff=self.RETRY_COOLDOWN,
                params={
                    "limit": 20,
                    "date.from": "2025-01-01T00:00:00.000Z",
                    "date.to": "now",
                    "offset": len(results),
                    "resourceTypes": [
                        "category",
                        "customer",
                        "customer-group",
                        "product",
                        "inventory-entry",
                        "review",
                        "product-discount",
                        "product-selection",
                        "product-type",
                        "channel",
                        "store",
                        "tax-category",
                        "zone",
                        "shopping-list",
                        "payment",
                        "quote",
                        "quote-request",
                        "staged-quote",
                        "state",
                        "type",
                    ],
                },
                url_override=self.HISTORY_API_URL + config["projectKey"],
            )
            if response and response["results"]:
                data = [
                    self.map_audit_log_to_csv_row(audit_log)
                    for audit_log in response["results"]
                ]
                self.write_attributes_to_csv(data, mode="a" if results else "w")
                results.extend(data)
                sleep(self.DEFAULT_COOLDOWN)
            else:
                break

    def map_audit_log_to_csv_row(self, audit_log):
        """Map audit log to csv row."""

        label = audit_log["label"]
        entity = label

        if isinstance(label, dict):
            if label["type"] == "OrderLabel":
                entity = (
                    f"{label.get('orderNumber')} for {label.get('customerEmail')}"
                )
            elif label["type"] == "LocalizedLabel":
                entity = label.get("value", {}).get("en-US", "")
            elif label["type"] == "StringLabel":
                entity = label.get("value", "")

        row = {
            "Modified by": audit_log["modifiedBy"]["id"],
            "Last modified": audit_log["modifiedAt"],
            "Action": audit_log["type"],
            "Changes": ", ".join(
                change["change"] for change in audit_log["changes"]
            ),
            "Current entity": entity,
            "Entity type": audit_log["resource"]["typeId"],
        }

        return row

    def write_attributes_to_csv(self, data, mode="a"):
        """Write attributes to CSV."""
        filename = f"audit_log_{datetime.now().strftime('%Y%m%d')}.csv"

        with open(filename, mode, newline="") as output_file:
            dict_writer = csv.DictWriter(
                output_file, fieldnames=data[0].keys(), delimiter="\t"
            )
            if mode == "w":
                dict_writer.writeheader()
            dict_writer.writerows(data)

        print(f"Wrote {len(data)} records in CSV '{filename}'")
