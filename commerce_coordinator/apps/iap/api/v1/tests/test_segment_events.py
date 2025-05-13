"""
Test suite for segment events utilities
"""

# pylint: disable=redefined-outer-name

from unittest.mock import patch, MagicMock
import pytest

from commercetools.platform.models import (
    CentPrecisionMoney,
    LineItem,
    PaymentMethodInfo
)
from commerce_coordinator.apps.iap.api.v1.segment_events import SegmentEventTracker


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


@patch("commerce_coordinator.apps.iap.api.v1.segment_events.track")
@patch("commerce_coordinator.apps.iap.api.v1.segment_events.get_product_from_line_item")
@patch(
        "commerce_coordinator.apps.iap.api.v1.segment_events.cents_to_dollars", 
        side_effect=lambda x: x.cent_amount / 100
    )
@patch("commerce_coordinator.apps.iap.api.v1.segment_events.sum_money")
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
    mock_cents_to_dollars.side_effect = lambda x: x.cent_amount / 100 if x else None

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

    SegmentEventTracker.emit_checkout_started_event(
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


@patch("commerce_coordinator.apps.iap.api.v1.segment_events.track")
@patch("commerce_coordinator.apps.iap.api.v1.segment_events.get_product_from_line_item")
def test_emit_product_added_event(
    mock_get_product_from_line_item,
    mock_track
):

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

    SegmentEventTracker.emit_product_added_event(
        lms_user_id=1,
        cart_id="cart123",
        standalone_price=mock_price,
        line_item=mock_line_item,
        discount_codes=[]
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


@patch("commerce_coordinator.apps.iap.api.v1.segment_events.track")
def test_emit_payment_info_entered_event(
    mock_track,
    mock_price,
    mock_payment_method
):

    SegmentEventTracker.emit_payment_info_entered_event(
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
    assert props["payment"] == "android_iap"
    assert props["is_mobile"] is True

@patch("commerce_coordinator.apps.iap.api.v1.segment_events.track")
@patch("commerce_coordinator.apps.iap.api.v1.segment_events.get_product_from_line_item")
@patch(
        "commerce_coordinator.apps.iap.api.v1.segment_events.cents_to_dollars",
        side_effect=lambda x: x.cent_amount / 100
    )
@patch("commerce_coordinator.apps.iap.api.v1.segment_events.sum_money")
def test_emit_order_completed_event(
    mock_sum_money,
    mock_cents_to_dollars,
    mock_get_product_from_line_item,
    mock_track,
    mock_price,
    mock_payment_method
):

    mock_sum_money.return_value = None
    mock_cents_to_dollars.side_effect = lambda x: x.cent_amount / 100 if x else None

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

    SegmentEventTracker.emit_order_completed_event(
        lms_user_id=1,
        cart_id="cart123",
        order_id="order123",
        standalone_price=mock_price,
        line_items=[mock_line_item],
        payment_method=mock_payment_method,
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
    assert props["tax"] is None
    assert props["coupon"] is None
    assert props["discount"] is None
    assert props["payment_method"] == "android_iap"
    assert props["processor_name"] == "android_iap"
    assert props["products"][0]["product_id"] == "course-v1:edX+DemoX+Demo_Course"
    assert props["is_mobile"] is True
