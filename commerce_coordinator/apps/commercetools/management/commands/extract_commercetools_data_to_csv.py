from datetime import datetime
import csv
from enum import Enum
from itertools import product

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
        # Specify product type to fetch
        product_type = ProductType.EDX_PROGRAM

        # Fetch products based on type
        products = self.fetch_products(product_type)

        # Write data to CSV
        self.write_attributes_to_csv(products, product_type)

    def fetch_products(self, product_type):
        limit = 500
        offset = 0
        products = []

        product_type_id = PROD_PRODUCT_TYPE_ID_MAPPING.get(product_type.value)

        while True:
            products_result = self.ct_api_client.base_client.products.query(
                limit=limit,
                offset=offset,
                where=f"productType(id=\"{product_type_id}\")"
            )
            for product in products_result.results:
                attributes = self.extract_product_attributes(product, product_type.value)
                products.extend(attributes)

            if products_result.offset + products_result.limit >= products_result.total:
                break
            offset += limit

        return products

    def extract_product_attributes(self, product, product_type):
        # Extract common product-level attributes
        common_attributes = {
            "product_type": product_type,
            "product_id": product.id,
            "product_key": product.key,
            "published_status": product.master_data.published,
            "name": product.master_data.current.name.get('en-US', ''),
            "slug": product.master_data.current.slug.get('en-US', ''),
            "description": (
                product.master_data.current.description.get('en-US', '')
                if product.master_data.current.description
                else ''
            ),
            "date_created": product.created_at,
            "master_variant_key": product.master_data.current.master_variant.key,
            "master_variant_sku": product.master_data.current.master_variant.sku,
            "master_variant_image_url": (
                product.master_data.current.master_variant.images[0].url
                if product.master_data.current.master_variant.images
                else None
            ),
        }

        product_rows = []  # This will hold the product and variant rows

        # Add the master variant attributes
        if len(product.master_data.current.variants) == 0:
            master_variant_attributes = {attr.name: attr.value for attr in
                                         product.master_data.current.master_variant.attributes}
            product_rows.append({**common_attributes, **master_variant_attributes})

        # Add attributes for each variant and create a separate row, including variant_key and variant_sku
        for variant in product.master_data.current.variants:
            variant_attributes = {attr.name: attr.value for attr in variant.attributes}
            variant_row = {
                **common_attributes,
                "variant_key": variant.key,  # Add variant_key
                "variant_sku": variant.sku,  # Add variant_sku
                "variant_image_url": (
                    variant.images[0].url
                    if variant.images
                    else None
                ),
                **variant_attributes,
            }
            # Create a new row for each variant, combining common product data with variant-specific attributes
            product_rows.append(variant_row)

        return product_rows

    def write_attributes_to_csv(self, products, product_type):
        if not products:
            print(f"No products found for type {product_type}.")
            return

        # Dynamically extract all unique keys across all product dictionaries
        keys = set()
        for product in products:
            keys.update(product.keys())

        # Convert keys set back to a list and sort them if you want a consistent order
        keys = sorted(list(keys))

        # Define CSV filename with product type and date
        filename = f"{product_type.value}_attributes_{datetime.now().strftime('%Y%m%d')}.csv"

        # Write to CSV
        with open(filename, "w", newline="") as output_file:
            dict_writer = csv.DictWriter(output_file, fieldnames=keys)
            dict_writer.writeheader()
            dict_writer.writerows(products)

        print(f"\n\n\n\n\n\n\nCSV file '{filename}' written successfully with {len(products)} records.")
