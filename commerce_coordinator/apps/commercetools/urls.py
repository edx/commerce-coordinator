"""
commercetools app URLS
"""

from django.urls import include, path

from commerce_coordinator.apps.commercetools.views import (
    MobileCourseVariantAddView,
    MobileStandalonePriceChangeView,
    OrderFulfillView,
    OrderReturnedView,
    OrderSanctionedView
)

app_name = 'commercetools'
urlpatterns = [
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    # EventBridge / CloudWatch Endpoints
    path('fulfill', OrderFulfillView.as_view(), name='fulfill'),
    path('mobile-course-variant-add', MobileCourseVariantAddView.as_view(), name='mobile-course-variant-add'),
    path(
        'mobile-standalone-price-change',
        MobileStandalonePriceChangeView.as_view(),
        name='mobile-standalone-price-change',
    ),
    path('sanctioned', OrderSanctionedView.as_view(), name='sanctioned'),
    path('returned', OrderReturnedView.as_view(), name='returned')
]
