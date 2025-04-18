import json

from commercetools.platform.models import (
    ProductDraft,
    ProductPriceModeEnum,
    ProductTypeResourceIdentifier,
    ProductVariantDraft
)

from commerce_coordinator.apps.commercetools.management.commands._ct_api_client_command import (
    CommercetoolsAPIClientCommand
)

product_json = '''



'''


class Command(CommercetoolsAPIClientCommand):
    help = "Create a commercetools product from a JSON string or file"

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

        product_type_data = product_data.get("productType")
        if product_type_data:
            product_type = ProductTypeResourceIdentifier(id=product_type_data["id"])
        else:
            print("\n\n\n\nMissing productType data.\n\n\n\n")
            return

        master_variant_data = product_data.get("masterVariant")
        variants_data = product_data.get("variants", [])

        master_variant = ProductVariantDraft(**master_variant_data)
        variants = [ProductVariantDraft(**variant) for variant in variants_data]

        product_draft_data = {
            "key": product_data.get("key"),
            "name": product_data.get("name"),
            "description": product_data.get("description"),
            "slug": product_data.get("slug"),
            "price_mode": ProductPriceModeEnum.STANDALONE,
            "publish": product_data.get("publish"),
            "tax_category": product_data.get("taxCategory"),
            "master_variant": master_variant,
            "variants": variants,
            "product_type": product_type
        }

        try:
            product_draft = ProductDraft(**product_draft_data)
            created_product = self.ct_api_client.base_client.products.create(draft=product_draft)
            print(f"\n\n\n\nSuccessfully created product with ID: {created_product.id}")
        except Exception as e:
            print(f"\n\n\n\nError creating product: {e}")
