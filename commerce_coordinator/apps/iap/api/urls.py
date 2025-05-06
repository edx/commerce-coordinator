from django.urls import include, re_path

from commerce_coordinator.apps.iap.api.v1 import urls as v1_mobile_urls

app_name = 'iap'
urlpatterns = [
    re_path(r'^v1/', include((v1_mobile_urls, 'v1'), namespace='v1')),
]
