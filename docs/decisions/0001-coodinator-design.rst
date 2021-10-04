#######################
0001 Coordinator Design
#######################

Status
******

**Draft**

Context
*******

edX's monolithic Ecommerce Service was meant to be a full-featured product catalog, discounting, and order management service and has grown in complexity for many years until it has become very hard to maintain, let alone evolve.  In that time, more and better hosted services have become available for solving many of these problems.

Decision
********

In contrast, this project will work as a modular coordinator between edX platform services and various hosted commerce solutions that offer payment processing, financial reporting, etc.

Consequences
************

This project will be highly modular
===================================

