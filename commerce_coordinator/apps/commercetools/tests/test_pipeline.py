from datetime import datetime, timezone
from typing import List, Optional

import requests_mock
from commercetools.platform.models import Customer, CustomerPagedQueryResponse, Order, OrderPagedQueryResponse
from conftest import APITestingSet, gen_example_customer, gen_order_history

from commerce_coordinator.apps.commercetools.catalog_info.constants import EdXFieldNames
from commerce_coordinator.apps.commercetools.catalog_info.foundational_types import TwoUCustomTypes
from commerce_coordinator.apps.core.constants import ORDER_HISTORY_PER_SYSTEM_REQ_LIMIT


class PipelineMocker:
    USER_ID = 127

    DATES_UNORDERED = [
        datetime(2020, 1, 1, tzinfo=timezone.utc),
        datetime(2020, 1, 3, tzinfo=timezone.utc),
        datetime(2020, 1, 2, tzinfo=timezone.utc)
    ]

    DATES_ORDERED = [  # Dates are DESC
        datetime(2020, 1, 3, tzinfo=timezone.utc),
        datetime(2020, 1, 2, tzinfo=timezone.utc),
        datetime(2020, 1, 1, tzinfo=timezone.utc)
    ]

    LIMIT = ORDER_HISTORY_PER_SYSTEM_REQ_LIMIT

    @staticmethod
    def request_mocker(client_set: APITestingSet, id_num=USER_ID, limit=LIMIT,
                       unsorted_dates: Optional[List[datetime]] = None) -> requests_mock.Mocker:
        dates = unsorted_dates if unsorted_dates else PipelineMocker.DATES_UNORDERED
        base_url = client_set.get_base_url_from_client()
        type_val = client_set.client.ensure_custom_type_exists(TwoUCustomTypes.CUSTOMER_TYPE_DRAFT)
        customer = gen_example_customer()
        orders = gen_order_history(len(dates))
        customer.custom.fields[EdXFieldNames.LMS_USER_ID] = id_num

        customer.custom.type.id = type_val.id

        client_set.backend_repo.customers.add_existing(customer)

        for i in range(0, len(dates)):  # assign mis-ordered dates, customer, and add to store
            order = orders[i]
            order.completed_at = dates[i]
            order.customer_id = customer.id
            client_set.backend_repo.orders.add_existing(order)

        mocker = requests_mock.Mocker(real_http=True, case_sensitive=False)
        mocker.get(
            f"{base_url}customers?"
            f"where=custom%28fields%28edx-lms_user_id%3D%3Aid%29%29"
            f"&limit=2"
            f"&var.id={PipelineMocker.USER_ID}",
            json=CustomerPagedQueryResponse(
                limit=limit, count=1, total=1, offset=0,
                results=client_set.fetch_from_storage('customer', Customer),
            ).serialize()
        )
        mocker.get(
            f"{base_url}orders?"
            f"where=customerId%3D%3Acid&"
            f"limit={limit}&"
            f"offset=0&"
            f"sort=completedAt+desc&"
            f"var.cid={PipelineMocker.USER_ID}",
            json=OrderPagedQueryResponse(
                limit=limit, count=1, total=1, offset=0,
                results=client_set.fetch_from_storage('order', Order),
            ).serialize()
        )

        return mocker
