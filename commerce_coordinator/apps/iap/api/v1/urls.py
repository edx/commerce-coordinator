from django.urls import path
from commerce_coordinator.apps.iap.api.v1.views import CreateOrderView

urlpatterns = [
    path("create-order/", CreateOrderView.as_view(), name="create_order"),
]
