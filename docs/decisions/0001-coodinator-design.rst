#######################
0001 Coordinator Design
#######################

Status
******

**Draft**

Context
*******

edX's monolithic Ecommerce Service was meant to be a full-featured product catalog, discounting, and order management service and has grown in complexity for many years until it has become very hard to maintain, let alone evolve.  In that time, more and better hosted services have become available for solving many of these problems, and complex use cases have evolved that make flexibility for Open edX operators vital.


Decisions
*********

- This application will be a Django-based independently deployed application with a MySQL backend database and redis cache.
- This application will work as a modular coordinator between edX platform services and various other hosted or home grown solutions that provide functionality relevant to commercial transactions.
- This application will not provide a customer-facing user interface.
- This application will not maintain state for business objects.


Consequences
************

Django based
============

The Commerce Coordinator will be a Django web service written in Python. This decision is to leverage the wealth of experience that the edX developers have in writing and running these services, allowing for a faster time to value and more stable deployment.

Highly modular
==============

The world of online commerce is rapidly changing, and with so many moving pieces it is important to Open edX operators to be able to use the services and tools that are the best fit for them, in the ways that they need to. As such we have decided to use a system of decoupled events to allow maximum flexibility in implementation. The exact details of the event mechanisms will be addressed in subsequent ADRs.

The system will allow for a set of messages and handlers to be configured to support any set of use cases (ex: Payment Received, Refund Requested). A set of messages and handlers may be included with the distribution that can be enabled via configuration which interact with various Open edX systems (for example LMS notified upon Payment Received), but the use of those messages and handlers is entirely optional. Additional Django Apps can be installed in the usual fashion which may offer additional handlers and new messages.

In addition to handlers and messages, the system will allow URL endpoints to be configured via the usual Django routing methods to receive incoming API calls / callbacks from external services. The usual Django app mechanisms can be used to add new URL endpoints and callback handlers which can, in turn, fire off other messages.

The expectation is that the combination of these functionalities will allow significant flexibility via configuration, and the ability to insert custom business logic where necessary to glue together functionality from different systems into one cohesive commerce solution.


No customer-facing user interface
=================================

The goal is to make this system the central coordinator of functionality from numerous other sources, not for it to be a one-to-one replacement for functionality currently in the edX Oscar-based Ecommerce system. As such, the expectation will be that any UI functionality will exist in 3rd party hosted services, micro-frontends, or other custom solutions that fill the specific need of the site operator. Any UI would be able to communicate with the public API of this service to retrieve information or perform actions on behalf of a user, however.

As this is a Django app, we *do* expect to use the Django Admin interface for administrative functionality such as configuration or storing Waffle flag state.


No business object storage
==========================

This system is intended to be a broker of messages between systems of record, and not a system of record itself. This should allow us to push the business logic that manages the details of that data to specialist systems which are best suited to those tasks.

For example, it should be possible to configure the Coordinator to broker messages between the following external services which own data:

- Course catalog service might manage
    - Course descriptions
    - Course run start and end dates
    - Pricing

- Fraud prevention service might manage
    - Rejected transactions
    - The Specially Designated Nationals and Blocked Persons list (SDN)

- Payment processing service might manage
    - Payment status
    - Refund status

- Marketing communication service might manage
    - Order receipt emails
    - Purchase attribution

- The edX LMS service might manage
    - Enrollment details

The Commerce Coordinator can serve as the generic interface by which information can be pulled or pushed across those systems in a way that makes them a cohesive commerce solution.

