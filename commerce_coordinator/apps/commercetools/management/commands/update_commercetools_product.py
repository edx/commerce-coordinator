import json

from commerce_coordinator.apps.commercetools.http_api_client import CTCustomAPIClient
from commerce_coordinator.apps.commercetools.management.commands._ct_api_client_command import (
    CommercetoolsAPIClientCommand
)

product_id = '21533075-1710-4cbc-88d2-a18ba4176fdd'
product_json = '''

{
        "version": 9,
        "actions": [
            {
              "action": "setDescription",
              "description": {
                "en-US": "<p>This course reflects the most current version of the PMP exam.</p>"
              }
            },
            {
                "action": "publish"
            }
        ]
    }


'''


class Command(CommercetoolsAPIClientCommand):
    help = "Update a commercetools product from a JSON string or file"

    def handle(self, *args, **options):
        if product_json:
            try:
                product_data = json.loads(product_json)
            except json.JSONDecodeError as e:
                self.stderr.write(f"Invalid JSON format: {e}")
                return
        else:
            print("\n\n\n\nNo JSON data provided.\n\n\n\n")
            return

        version = product_data.get("version")
        actions = product_data.get("actions")

        if not product_id or not version or not actions:
            print("\n\n\n\nMissing product ID, version, or actions.\n\n\n\n")
            return

        # Initialize the custom commercetools client
        ct_client = CTCustomAPIClient()

        # Prepare the data for updating the product
        update_payload = {
            "version": version,
            "actions": actions
        }

        # Make the request to update the product
        endpoint = f"products/{product_id}"
        response = ct_client._make_request(
            method="POST",
            endpoint=endpoint,
            json=update_payload
        )

        if response:
            print(f"\n\n\n\n\nSuccessfully updated product with ID: {response.get('id')}\n\n\n\n\n")
        else:
            print("\n\n\n\n\nError updating product.\n\n\n\n\n\n")
