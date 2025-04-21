################################################
Webhook-Based Fulfillment Service Communication
################################################

Status
******

**Draft**

Context
*******

We are designing a new fulfillment engine as a Django-based service (Order Fulfillment, or OF) to process fulfillment (e.g., fulfilling in LMS) requests initiated by the Commerce Coordinator (CC) service. These services will be maintained by different organizations — OF by 2U, and CC by Red Ventures.

To maintain clear service boundaries and reduce coupling, we need a secure, reliable, and decoupled communication model. The mechanism must work across platforms, be framework-agnostic, and ensure message integrity and authenticity — similar to webhooks used by platforms like Stripe and PayPal.

This ADR documents the different implementation approaches and rationale for choosing a custom webhook-based approach.

Decision: Custom Webhook-Based Implementation
*********************************************

We will implement a custom, HMAC-secured webhook mechanism, inspired by Stripe, for communication between services. The key security feature of this approach is the use of a shared secret key between the Commerce Coordinator (CC) and Order Fulfillment (OF) services to generate and verify HMAC (Hash-based Message Authentication Code) signatures.

How It Works?
=============

Request Generation (`commerce-coordinator`)
-------------------------------------------

1. **Prepare Payload and Timestamp**

- Construct the payload (e.g., fulfillment request data) and add a UNIX timestamp.
- Example payload and timestamp:

.. code-block:: python

         import json
         import time

         payload = json.dumps({
             "order_id": "12345",
             "customer": "John Doe",
             "items": [{"sku": "A001", "quantity": 2}],
         })
         timestamp = str(int(time.time()))

2. **Generate Signature**

- Create an HMAC-SHA256 signature using the shared secret, combining the timestamp and payload.
- Example code to generate the signature:


.. code-block:: python

         import hmac
         import hashlib

         shared_secret = b"your_shared_secret"
         message = timestamp + payload
         signature = hmac.new(shared_secret, message.encode(), hashlib.sha256).hexdigest()


- The `shared_secret` will be encrypted and stored securely in edx-internal for both services, ensuring consistent usage. It will be used again in while validating the request in the `order-fulfillment` service. (see below)

3. **Send the Request**

- The `commerce-coordinator` sends the request to the `order-fulfillment` service with the signature and timestamp as headers.
- Example request with headers:

.. code-block:: python

         import requests

         url = "https://order-fulfillment.example.com/webhook"
         headers = {
             "X-Webhook-Timestamp": timestamp,
             "X-Webhook-Signature": signature,
         }

         response = requests.post(url, data=payload, headers=headers)

Validation (`order-fulfillment`)
--------------------------------

1. **Check Timestamp**

- The receiving service (`order-fulfillment`) validates the timestamp to ensure it’s within a 5-minute window to prevent replay attacks.
- Example validation of timestamp:

.. code-block:: python

         import time

         MAX_ALLOWED_DELAY = 5 * 60  # 5 minutes

         received_timestamp = int(request.headers['X-Webhook-Timestamp'])
         current_timestamp = int(time.time())
         if abs(current_timestamp - received_timestamp) > MAX_ALLOWED_DELAY:
             raise ValueError("Request timestamp is too old.")

2. **Recompute HMAC Using Shared Secret**

- The service recomputes the HMAC signature using the timestamp and payload to verify the integrity of the message.
- Example signature computation:

.. code-block:: python

         received_signature = request.headers['X-Webhook-Signature']
         expected_signature = hmac.new(shared_secret, (str(received_timestamp) + request.data).encode(), hashlib.sha256).hexdigest()

         if not hmac.compare_digest(received_signature, expected_signature):
             raise ValueError("Invalid signature.")

3. **Perform Constant-Time Comparison**

- To prevent timing attacks, ensure that signature comparison is done in constant time.
- Example constant-time comparison:

.. code-block:: python

         hmac.compare_digest(received_signature, expected_signature)

If the timestamp is valid and the signatures match, the request is processed.

Pros
====

- **Secure Communication**: Since HMAC-based webhooks are a known and trusted model, there is less need for a new security review from scratch.
- **Encrypted Shared Key**: They shared key will be encrypted and stored in `edx-internal` for both CC and OF.
- **Proven Pattern**: Inspired by widely-used, industry-standard webhook models (e.g., Stripe), which are well-tested and understood.
- **Cross-Platform Compatible**: Works across services implemented in different tech stacks, with no dependency on platform-specific features or SDKs.
- **Decoupled Architecture**: Clean separation between services thus reducing service coupling.
- **Flexibility Control**: Full ownership over how requests are validated, retried, and logged.
- **No External Dependency**: Does not rely on third-party cloud infrastructure (e.g., AWS EventBridge), enabling more flexibility and control.
- **Zero Infrastructure Cost**: No additional cost associated with using a cloud event bus or message queue. Relies on HTTPS and standard cryptographic libraries.
- **Lightweight and Fast**: Low overhead in both message size and processing latency. Uses minimal resources and fast cryptographic operations.
- **Custom Retry Logic**: Since its a custom HTTP based solution, we have the flexibility to implement retry mechanism.
- **No Payload Limits**: Unlike EventBridge (which enforces a ~256 KB size limit), this model allows payload sizes as needed.
- **Single Sender–Receiver**: The communication is between one sender and one receiver and be enhanced as needed.

Cons
====

- **Requires Custom Implementation**: Unlike managed services like AWS EventBridge, this solution requires us to build, test, and maintain the retry logic.
- **Manual Key Management**: Secrets must be managed and rotated manually or via internal tooling, which adds operational overhead and potential for misconfiguration if not handled properly.
- **No Built-in Delivery Guarantees**: Unlike EventBridge, which guarantees at-least-once delivery with retries, we need to implement our own retry mechanism.

Rejected Alternatives
*********************


1. Open edX Kafka Event Bus
===========================

The `kafka-event-bus` is an asynchronous event system used across Open edX services, based on the pub/sub model using Django Signals (via `OpenEdxPublicSignals`). It extends internal Django signals to communicate between distributed services.

**Cons**

- **Coupling to 2U Infrastructure**: The Kafka bus is managed through `edx-terraform` under 2U ownership, introducing infra and org-level dependencies.
- **Tied to Open edX Events**: Requires all events to be defined in the `openedx-events` repo, adding further tight coupling.
- **Dependent on OpenEdxPublicSignals**: Built around `OpenEdxPublicSignals`, which assumes deeper integration into Open edX internals.
- **Django-Specific**: Primarily designed for Django-based services, which is limiting since future consumers may not use Django.

The strong dependency on Open edX and Django conflicts with our architectural goals of service independence and platform neutrality. Thus, we ruled this option out.

**References**

- `How to start using the Event Bus (Open edX) <https://openedx.atlassian.net/wiki/spaces/AC/pages/3508699151/How+to+start+using+the+Event+Bus>`_
- `How to Use the Event Bus on edX.org (2U) <https://2u-internal.atlassian.net/wiki/spaces/AT/pages/174555142/How+to+Use+the+Event+Bus+edX.org+2+of+2>`_

2. AWS EventBridge
==================

AWS EventBridge supports asynchronous service communication through an event bus and API destinations, offering a robust and managed pub/sub system.

**Cons**

- **Operational Cost**: Additional cost for message processing and API destinations.
- **Infrastructure Complexity**: Setting up EventBridge involves managing IAM users, access credentials, Secrets Manager, API destinations, and event routing rules — increasing operational burden.
- **Local Development Overhead**: Requires mocking or local setup tools to simulate EventBridge.

While AWS EventBridge provides powerful features such as built-in retries, scalable pub/sub architecture, cross-platform compatibility, and secure bidirectional messaging, the added cost and infrastructure overhead outweigh the benefits for a relatively simple point-to-point communication use case like ours.

3. Third-Party Webhook Libraries
================================

Third party open-source libraries (e.g., `django-webhook <https://django-webhook.readthedocs.io/en/latest/>`_) offer prebuilt functionality for secure HMAC-based webhook signing and verification.

**Cons**

- **Lack of Cross-Platform Support**: No single library works natively across all major languages like Python, Node.js, etc.
- **Minimal Value Add**: HMAC signing and timestamp checks are simple to implement with native modules (`hmac`, `hashlib`, `crypto`, etc.).
- **Maintenance Risk**: Reliance on third-party maintainers with uncertain support or updates.
- **Reduced Flexibility**: Custom behavior or advanced integrations may be harder to achieve.
- **Learning Overhead**: Each library adds new abstractions that need to be understood and tested.

While these libraries provide basic utilities like signature verification, they do not offer enough value beyond what native modules can accomplish. Considering the simplicity of our use case and need for full control, we opted against introducing external dependencies.
