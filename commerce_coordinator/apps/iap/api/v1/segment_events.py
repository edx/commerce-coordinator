from typing import Optional
from commercetools.platform.models import (
    LineItem,
    CentPrecisionMoney
)
from commerce_coordinator.apps.core.segment import track
from commerce_coordinator.apps.iap.api.v1.utils import (
    cents_to_dollars,
    sum_money,
    get_product_from_line_item
)

class SegmentEventTracker:
    """Handles analytics tracking with Segment."""

    @staticmethod
    def emit_checkout_started_event(
        *,
        lms_user_id: int,
        cart_id: str,
        standalone_price: CentPrecisionMoney,
        line_items: list[LineItem],
        discount_codes: list[dict[str, any]],
        discount_on_line_items: list[CentPrecisionMoney],
        discount_on_total_price: Optional[CentPrecisionMoney] = None
    ) -> None:
        
        """
        Triggers the "Checkout Started" event on Segment with relevant cart and product details.

        Args:
            lms_user_id (int): ID of the user initiating the checkout.
            cart_id (str): Unique identifier for the shopping cart.
            standalone_price (CentPrecisionMoney): The total price of the cart before discounts.
            line_items (list[LineItem]): List of line items in the cart.
            discount_codes (list[dict]): List of discount code dictionaries applied to the order.
            discount_on_line_items (list[CentPrecisionMoney]): Discounts applied to individual items.
            discount_on_total_price (Optional[CentPrecisionMoney or list[CentPrecisionMoney]]): 
                Discount applied to the entire order, if any.

        Emits:
            A "Checkout Started" event with details such as:
                - cart_id, checkout_id
                - currency and price values
                - applied coupon and total discount
                - product breakdown
                - mobile flag (defaulted to True as server purchase events are only for mobile)
        """
        discount_code = (
            discount_codes[-1]["code"] 
            if discount_codes and "code" in discount_codes[-1] 
            else None
        )
        
        discount_in_dollars = cents_to_dollars(
            sum_money(discount_on_total_price, discount_on_line_items)
        )

        products = [
            get_product_from_line_item(item, standalone_price)
            for item in line_items
        ]

        event_props = {
            "cart_id": cart_id,
            "checkout_id": cart_id,
            "currency": standalone_price.currency_code,
            "revenue": cents_to_dollars(standalone_price),
            "value": cents_to_dollars(standalone_price),
            "coupon": discount_code,
            "discount": discount_in_dollars,
            "products": products,
            "is_mobile": True
        }

        track(
            lms_user_id=lms_user_id,
            event='Checkout Started',
            properties=event_props
        )


    def emit_product_added_event(
        *,
        lms_user_id: int,
        cart_id: str,
        standalone_price: CentPrecisionMoney,
        line_item: LineItem,
        discount_codes: list[dict[str, any]],
    ) -> None:
        
        """
        Triggers the "Product Added" event on Segment with product and cart details.

        Args:
            lms_user_id (int): ID of the user who added the product to the cart.
            cart_id (str): Unique identifier of the user's cart.
            standalone_price (CentPrecisionMoney): Price object for the added product before discounts.
            line_item (LineItem): The product line item that was added to the cart.
            discount_codes (list[dict[str, any]]): List of discount code dictionaries applied to the cart.

        Emits:
            A "Product Added" event with details including:
                - Product metadata such as ID, name, SKU, category, price, etc.
                - Cart ID and checkout ID
                - Applied coupon (if any)
                - Device context (hardcoded as mobile)
        """
     
        discount_code = (
            discount_codes[-1]["code"] 
            if discount_codes and "code" in discount_codes[-1] 
            else None
        )

        product_info = get_product_from_line_item(line_item, standalone_price)

        event_props = {
            "cart_id": cart_id,
            "checkout_id": cart_id,
            "coupon": discount_code,
            **product_info,
            "is_mobile": True
        }

        track(
            lms_user_id=lms_user_id,
            event='Product Added',
            properties=event_props
        )


    def emit_payment_info_entered_event(
        *,
        lms_user_id: int,
        cart_id: str,
        standalone_price: CentPrecisionMoney,
        payment_method: str
    ) -> None:
        
        """
        Triggers the "Payment Info Entered" event on Segment when a user enters payment information.

        Args:
            lms_user_id (int): ID of the user entering payment information.
            cart_id (str): Unique identifier of the user's shopping cart.
            standalone_price (CentPrecisionMoney): The total price of the cart used to extract currency.

        Emits:
            A "Payment Info Entered" event with details such as:
                - cart_id and checkout_id
                - currency code
                - payment method (defaulted to 'android-iap')
                - is_mobile flag (set to True for mobile platforms)
        """

        event_props = {
            "cart_id": cart_id,
            "checkout_id": cart_id,
            "currency": standalone_price.currency_code,
            "payment": payment_method,
            "is_mobile": True
        }

        track(
            lms_user_id=lms_user_id,
            event='Payment Info Entered',
            properties=event_props
        )




