
Intercommunication details
==========================
Details about integration points that will be routed through the commerce coordinator

Order History Page
~~~~~~~~~~~~~~~~~~
We link to an order history page from a user dropdown menu on non-staff accounts (frontend-component-header’s AuthenticatedUserDropdown
component), and the destination url is: https://orders.edx.org/orders

This order history page is served from the frontend-app-ecommerce repo. Here are the steps to retrieve that data:

1. When the OrderHistoryPage component mounts, it calls fetchOrders.

2. That fetchOrders action is set defined in `actions.js`_. The `saga`_ uses generator functions to call getOrders and yield objects to the middleware,
and the `reducer`_ updates the state.

3. The getOrders function is defined in service.js, where it sets a data variable by `making an async call`_ to the ecommerce orders api.

MODIFICATIONS COMING:

1. We'll create a new 'orders' app under which we define an 'orders_requested' receiver function (using coordinator_receiver decorator) in signals.py. 
This function will call that ecommerce endpoint and yield the results properly. 

2. We'll update that `making an async call`_ code to fire the new 'orders_requested' signal with suitable payload (so the new code executes)

.. _actions.js: https://github.com/openedx/frontend-app-ecommerce/blob/f425c4b5369947449758ea96cfecdf207689d71a/src/order-history/actions.js
.. _saga: https://github.com/openedx/frontend-app-ecommerce/blob/f425c4b5369947449758ea96cfecdf207689d71a/src/order-history/saga.js#L14
.. _reducer: https://github.com/openedx/frontend-app-ecommerce/blob/f425c4b5369947449758ea96cfecdf207689d71a/src/order-history/reducer.js
.. _making an async call: https://github.com/openedx/frontend-app-ecommerce/blob/f425c4b5369947449758ea96cfecdf207689d71a/src/order-history/service.js#L13

