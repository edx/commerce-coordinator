"""
Test suite for segment events utilities
"""

# pylint: disable=redefined-outer-name

from unittest.mock import MagicMock, patch

import pytest
from commercetools.platform.models import CentPrecisionMoney, LineItem, PaymentMethodInfo, TaxedPrice

from commerce_coordinator.apps.iap.segment_events import (
    emit_cart_viewed_event,
    emit_checkout_started_event,
    emit_order_completed_event,
    emit_payment_info_entered_event,
    emit_product_added_event
)


@pytest.fixture
def mock_price():
    return CentPrecisionMoney(cent_amount=10000, currency_code="USD", fraction_digits=2)


@pytest.fixture
def mock_payment_method():
    return PaymentMethodInfo(
        payment_interface='android_iap',
        method='credit card',
        name='android_iap'
    ).payment_interface


@pytest.fixture
def mock_line_item():

    """
    Mock line item object
    """

    def make_attr(name, value):
        attr = MagicMock()
        attr.name = name
        attr.value = value
        return attr

    variant = MagicMock()
    variant.sku = "demo-sku"
    variant.attributes = [
        make_attr("primary-subject-area", "business"),
        make_attr("url-course", "https://example.com/course"),
        make_attr("lob", "edx"),
        make_attr("brand-text", "edX"),
        make_attr("course-key", "course-v1:edX+DemoX+Demo_Course"),
    ]

    variant.images = ["https://example.com/image.jpg"]

    product_type = MagicMock()
    product_type.obj.key = "edx_course_entitlement"
    product_type.obj.name = "edX Course"

    line_item = MagicMock(spec=LineItem)
    line_item.product_key = "edX+DemoX"
    line_item.name = {"en-US": "Demo Course"}
    line_item.product_type = product_type
    line_item.quantity = 1
    line_item.variant = variant

    return line_item


@patch("commerce_coordinator.apps.iap.segment_events.track")
@patch("commerce_coordinator.apps.iap.segment_events.get_product_from_line_item")
@patch(
    "commerce_coordinator.apps.iap.segment_events.cents_to_dollars",
    side_effect=lambda x: x.cent_amount / pow(
        10, x.fraction_digits if hasattr(x, 'fraction_digits') else 2
    )
)
@patch("commerce_coordinator.apps.iap.segment_events.sum_money")
def test_emit_checkout_started_event(
    mock_sum_money,
    mock_cents_to_dollars,
    mock_get_product_from_line_item,
    mock_track,
    mock_price
):

    """
    Test for test_emit_checkout_started_event utility
    """

    mock_sum_money.return_value = None
    mock_cents_to_dollars.side_effect = lambda x: x.cent_amount / pow(
        10, x.fraction_digits if hasattr(x, 'fraction_digits') else 2
    ) if x else None

    mock_get_product_from_line_item.return_value = {
        "product_id": "course-v1:edX+DemoX+Demo_Course",
        "sku": "demo-sku",
        "name": {"en-US": "Demo Course"},
        "price": 100.0,
        "quantity": 1,
        "category": "business",
        "url": "https://example.com/course",
        "lob": "edx",
        "image_url": "https://example.com/image.jpg",
        "brand": "edX",
        "product_type": "edX Course"
    }

    emit_checkout_started_event(
        lms_user_id=1,
        cart_id="cart123",
        standalone_price=mock_price,
        line_items=[mock_line_item],
        discount_codes=[],
        discount_on_line_items=[],
        discount_on_total_price=None
    )

    mock_track.assert_called_once()
    _, kwargs = mock_track.call_args

    assert kwargs["lms_user_id"] == 1
    assert kwargs["event"] == "Checkout Started"
    props = kwargs["properties"]
    assert props["cart_id"] == "cart123"
    assert props["coupon"] is None
    assert props["discount"] is None
    assert props["currency"] == "USD"
    assert props["revenue"] == 100.0
    assert props["value"] == 100.0
    assert props["is_mobile"] is True
    assert props["products"][0]["product_id"] == "course-v1:edX+DemoX+Demo_Course"


@patch("commerce_coordinator.apps.iap.segment_events.track")
@patch("commerce_coordinator.apps.iap.segment_events.get_product_from_line_item")
def test_emit_product_added_event_single_item(
    mock_get_product_from_line_item,
    mock_track,
    mock_price,
    mock_line_item
):
    """Test Product Added event with single item cart"""

    mock_get_product_from_line_item.return_value = {
        "product_id": "course-v1:edX+DemoX+Demo_Course",
        "sku": "demo-sku",
        "name": {"en-US": "Demo Course"},
        "price": 100.0,
        "quantity": 1,
        "category": "business",
        "url": "https://example.com/course",
        "lob": "edx",
        "image_url": "https://example.com/image.jpg",
        "brand": "edX",
        "product_type": "edX Course"
    }

    emit_product_added_event(
        lms_user_id=1,
        cart_id="cart123",
        standalone_price=mock_price,
        line_item=mock_line_item,
        discount_codes=[],
        line_items=[mock_line_item]  # Single item cart
    )

    mock_track.assert_called_once()
    _, kwargs = mock_track.call_args

    assert kwargs["lms_user_id"] == 1
    assert kwargs["event"] == "Product Added"
    props = kwargs["properties"]
    assert props["cart_id"] == "cart123"
    assert props["checkout_id"] == "cart123"
    assert props["coupon"] is None
    assert props["product_id"] == "course-v1:edX+DemoX+Demo_Course"
    assert props["is_mobile"] is True
    assert props["multi_item_cart_enabled"] is False


@patch("commerce_coordinator.apps.iap.segment_events.track")
@patch("commerce_coordinator.apps.iap.segment_events.get_product_from_line_item")
def test_emit_product_added_event_multi_item(
    mock_get_product_from_line_item,
    mock_track,
    mock_price,
    mock_line_item
):
    """Test Product Added event with multi-item cart"""

    mock_get_product_from_line_item.return_value = {
        "product_id": "course-v1:edX+DemoX+Demo_Course",
        "sku": "demo-sku",
        "name": {"en-US": "Demo Course"},
        "price": 100.0,
        "quantity": 1,
        "category": "business",
        "url": "https://example.com/course",
        "lob": "edx",
        "image_url": "https://example.com/image.jpg",
        "brand": "edX",
        "product_type": "edX Course"
    }

    # Create a second line item for multi-item cart
    mock_line_item_2 = MagicMock()
    mock_line_item_2.name = {"en-US": "Second Course"}
    mock_line_item_2.variant.sku = "demo-sku-2"
    mock_line_item_2.quantity = 1
    mock_line_item_2.product_key = "test-sku-2"

    emit_product_added_event(
        lms_user_id=1,
        cart_id="cart123",
        standalone_price=mock_price,
        line_item=mock_line_item,
        discount_codes=[],
        line_items=[mock_line_item, mock_line_item_2]  # Multi-item cart
    )

    mock_track.assert_called_once()
    _, kwargs = mock_track.call_args

    assert kwargs["lms_user_id"] == 1
    assert kwargs["event"] == "Product Added"
    props = kwargs["properties"]
    assert props["cart_id"] == "cart123"
    assert props["checkout_id"] == "cart123"
    assert props["coupon"] is None
    assert props["product_id"] == "course-v1:edX+DemoX+Demo_Course"
    assert props["is_mobile"] is True
    assert props["multi_item_cart_enabled"] is True


@patch("commerce_coordinator.apps.iap.segment_events.track")
def test_emit_payment_info_entered_event(
    mock_track,
    mock_price,
    mock_payment_method
):

    emit_payment_info_entered_event(
        lms_user_id=1,
        cart_id="cart123",
        standalone_price=mock_price,
        payment_method=mock_payment_method
    )

    mock_track.assert_called_once()
    _, kwargs = mock_track.call_args

    assert kwargs["lms_user_id"] == 1
    assert kwargs["event"] == "Payment Info Entered"
    props = kwargs["properties"]
    assert props["cart_id"] == "cart123"
    assert props["checkout_id"] == "cart123"
    assert props["currency"] == "USD"
    assert props["payment_method"] == mock_payment_method
    assert props["is_mobile"] is True


@patch("commerce_coordinator.apps.iap.segment_events.track")
@patch("commerce_coordinator.apps.iap.segment_events.get_product_from_line_item")
@patch(
    "commerce_coordinator.apps.iap.segment_events.cents_to_dollars",
    side_effect=lambda x: x.cent_amount / pow(
        10, x.fraction_digits if hasattr(x, 'fraction_digits') else 2
    )
)
@patch("commerce_coordinator.apps.iap.segment_events.sum_money")
def test_emit_order_completed_event(
    mock_sum_money,
    mock_cents_to_dollars,
    mock_get_product_from_line_item,
    mock_track,
    mock_price,
    mock_payment_method
):

    mock_sum_money.return_value = None
    mock_cents_to_dollars.side_effect = lambda x: x.cent_amount / pow(
        10, x.fraction_digits if hasattr(x, 'fraction_digits') else 2
    ) if x else None

    mock_get_product_from_line_item.return_value = {
        "product_id": "course-v1:edX+DemoX+Demo_Course",
        "sku": "demo-sku",
        "name": {"en-US": "Demo Course"},
        "price": 100.0,
        "quantity": 1,
        "category": "business",
        "url": "https://example.com/course",
        "lob": "edx",
        "image_url": "https://example.com/image.jpg",
        "brand": "edX",
        "product_type": "edX Course"
    }

    mock_tax_amount = CentPrecisionMoney(
        cent_amount=0, currency_code="USD", fraction_digits=2
    )
    mock_tax = TaxedPrice(
        total_tax=mock_tax_amount,
        total_gross=mock_price,
        total_net=mock_price,
        tax_portions=[],
    )

    mock_processor_name = "android iap"

    emit_order_completed_event(
        lms_user_id=1,
        cart_id="cart123",
        order_id="order123",
        tax=mock_tax,
        standalone_price=mock_price,
        line_items=[mock_line_item],
        payment_method=mock_payment_method,
        processor_name=mock_processor_name,
        discount_codes=[],
        discount_on_line_items=[],
        discount_on_total_price=None
    )

    mock_track.assert_called_once()
    _, kwargs = mock_track.call_args

    assert kwargs["lms_user_id"] == 1
    assert kwargs["event"] == "Order Completed"
    props = kwargs["properties"]
    assert props["order_id"] == "order123"
    assert props["checkout_id"] == "cart123"
    assert props["currency"] == "USD"
    assert props["total"] == 100.0
    assert props["tax"] == 0
    assert props["coupon"] is None
    assert props["discount"] is None
    assert props["payment_method"] == "android_iap"
    assert props["processor_name"] == "android iap"
    assert props["products"][0]["product_id"] == "course-v1:edX+DemoX+Demo_Course"
    assert props["is_mobile"] is True


@patch('commerce_coordinator.apps.iap.segment_events.track')
def test_emit_cart_viewed_event(mock_track, mock_price, mock_line_item):
    """
    Test that the Cart Viewed event is emitted with correct properties and multiple products support
    """
    emit_cart_viewed_event(
        lms_user_id=1,
        cart_id="cart123",
        standalone_price=mock_price,
        line_items=[mock_line_item],
        discount_codes=[],
        discount_on_line_items=[],
        discount_on_total_price=None
    )

    mock_track.assert_called_once()
    _, kwargs = mock_track.call_args

    assert kwargs["lms_user_id"] == 1
    assert kwargs["event"] == "Cart Viewed"
    props = kwargs["properties"]
    assert props["cart_id"] == "cart123"
    assert props["currency"] == "USD"
    assert props["value"] == 100.0
    assert props["coupon"] is None
    assert props["discount"] is None
    assert props["products"][0]["product_id"] == "course-v1:edX+DemoX+Demo_Course"
    assert props["products"][0]["position"] == 1
    assert props["multi_item_cart_enabled"] is False  # Cannot determine cart state without context


@patch('commerce_coordinator.apps.iap.segment_events.track')
def test_emit_cart_viewed_event_multiple_products(mock_track, mock_price, mock_line_item):
    """
    Test that the Cart Viewed event handles multiple products correctly
    """
    # Create a second line item
    mock_line_item_2 = MagicMock()
    mock_line_item_2.name = {"en-US": "Second Course"}
    mock_line_item_2.variant.sku = "demo-sku-2"
    mock_line_item_2.variant.attributes = []
    mock_line_item_2.price.value = mock_price
    mock_line_item_2.quantity = 1
    mock_line_item_2.id = "line-item-2"

    emit_cart_viewed_event(
        lms_user_id=1,
        cart_id="cart123",
        standalone_price=mock_price,
        line_items=[mock_line_item, mock_line_item_2],
        discount_codes=[],
        discount_on_line_items=[],
        discount_on_total_price=None
    )

    mock_track.assert_called_once()
    _, kwargs = mock_track.call_args

    assert kwargs["lms_user_id"] == 1
    assert kwargs["event"] == "Cart Viewed"
    props = kwargs["properties"]
    assert props["cart_id"] == "cart123"
    assert len(props["products"]) == 2
    assert props["products"][0]["position"] == 1
    assert props["products"][1]["position"] == 2
    assert props["multi_item_cart_enabled"] is True  # Multiple items cart


