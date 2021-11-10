###########################
0003 Internal Communication
###########################

Status
******

**Draft**


Context
*******

Per previous ADRs, Commerce Coordinator is intended to be a highly decoupled, modular, asynchronous platform for handling a wide variety of use cases and workflows. In order to allow for flexibility in configuration and extensibility the CC needs to have a loosely coupled internal architecture that allows for pluggable components to work with the same events.


Decisions
*********

- This application will recommend using Django applications as extension points
- This application will use Django signals as the primary means of communicating between extensions
- Enhancements will be made to the default Django signal behavior to support greater discoverability, configurability, and self-documentation


Consequences
************

Django Applications as Extension Points
=======================================

While any Python package can be installed and called from inside the Commerce Coordinator, using Django applications as extension points enables several key pieces of functionality:

- Extensions can add API endpoints for triggering workflows and callbacks
- Extensions can add Admin UI functionality
- Extensions can store data in custom Django models (discouraged, but could be useful for configuration)
- Extensions can create new Django signals
- Extensions can take advantage of our custom Django signal enhancements (see below)
- Extensions will be configurable via standard Django methodology and deployed in well understood ways


Django Signals for Communication
================================

`Django signals`_ allow messages to be sent to loosely coupled, unrelated components easily, and allow new extensions to listen to existing signals with no changes to the sender. Combining signals with Django apps allows a lot of flexibility in terms of future growth and deployment. Different areas of functionality could have their own instances, be pulled into other Django services, or have their Celery tasks moved into a message bus architecture in a lower impact way than if the code were written as traditional APIs.

The decision does create some complexity around the fact that signal handlers do not have a determistic order and that they are unable to return values to be used, however these are also the strengths that allow future modular growth and message bus implementation and are accepted as guardrails to keep our current implementation uncoupled.


.. _Django signals: https://docs.djangoproject.com/en/3.2/topics/signals/


Django Signal Enhancements
==========================

By default the connections between signals and their configured handlers can be difficult to understand. Additionally simply using the signal ``send()`` method can cause receivers to not get a message if one receiver fails. To mitigate these issues we have decided to make some enhancements as outlined below:

- The mapping of custom Commerce Coordinator signals and handlers will be created in configuration and enforced at app startup, including assurances that other handlers have not been connected to our signals in other ways.
- A custom subclass of ``django.core.signals.Signal`` will be created that only allows ``send_robust`` and wraps logging and error handling functionality to ensure that all handlers are called and that we are able to trace exceptions through the system.


Rejected Alternatives
*********************

A lengthy investigation was undertaken to look at several options for making this system loosely coupled and easily extensible.

Alternatives that were investigated and rejected:

- Using APIs & Callbacks
    - Rejected due to:
        - Greater possibilities of leaky abstractions / business logic leaking into the core
        - Greater difficulty moving to a more robust message bus solution when edX adopts one in the future
        - Greater difficulty moving components to their own microservices should that become desireable in the future
- Implementing / requiring an external message bus (such as Kafka)
    - Rejected due to:
        - Adding a complicated, expensive service to the platform
        - Time needed to pilot, develop, and productionalize a new service

