############################################
0004 Openedx-Filters for Close Communication
############################################

Status
******

**Draft**

.. Standard statuses
    - **Draft** if the decision is still preliminary and in experimental phase
    - **Accepted** *(date)* once it is agreed upon
    - **Superseded** *(date)* with a reference to its replacement if a later ADR changes or reverses the decision

Context
*******

As outlined in `ADR-3 <./0003-internal-communication.rst>`__, Django signals provide excellent decoupling of components and we will be extending them to improve tracing/debugging, validation, and holistic system comprehension.

There are cases for which signals are a poor fit when a component or action requires a direct response, however, we still want the source of that response data to be be decoupled and highly configurable.

There is substantial cost to having multiple distinct but similar mechanisms in an ecosystem; conversely there are benefits to using a common foundation as long as basically serves the need, even if it may not fit as well as a bespoke solution.

  - Shared development and maintenence burdon
  - Skills and knowledge translation

- `Openedx-filters <https://github.com/openedx/openedx-filters>`__ is a mechanism being developed to make the edx-platform project more extensible, and specifically to allow configurable functionality that augments, filters, or transforms data at key points in various processes.  It is expressly designed to compliment signals-driven extensions.

Decision
********

When signals are not feasible for component communication, we will use openedx-filters.

Consequences
************

- Components that communicate relatively directly are more tightly coupled, so when possible try to keep things loose enough to use signal, background tasks, etc.

- Coordinator will be extensible using more-or-less the same mechanisms as edx-platform; experience extending the LMS will transfer to building and extending Commerce Coordinator workflows.

- As with signals, we will need to subclass and extend parts of openedx-filters to improve reliability, tracability, validation, and other broad project goals.

  - Suppress the "fail silently" option
  - Add tracing of pipeline steps
  - Add validation and other support tooling
