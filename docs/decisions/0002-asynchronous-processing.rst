############################
0002 Asynchronous Processing
############################

Status
******

**Draft**

Context
*******

The Commerce Coordinator is most significantly a broker for network calls to other services. This pattern can introduce latency and frailty into the entire service when a downstream service is experiencing performance or availability issues. EdX has experience mitigating these kinds of issues by using a message queue and separating the processing of the networking requests from the processing of APIs and other low-latency work using Celery queues and tasks.

Decisions
*********

- This application will primarily utilize an asynchronous message queue to handle communication with other services by default.
- This application will utilize Celery as the message broker.
- Celery tasks will be run in the context of Celery worker processes, not in the API-providing Commerce Coordinator service.
- The API service and extensions should do very little actual work and will primarily be responsible for routing calls to Celery tasks which should do the majority of the processing.
- Code for API endpoints, Celery tasks, and task handlers should be co-located in one place and released together.

Consequences
************

Unless there is a very compelling reason not to, all message handling that calls to external services from the Commerce Coordinator will be done in Celery tasks. Those tasks will run on a different set of servers / in different processes than the ones which power the Commerce Coordinator API, allowing the API to be resilient to downstream service issues.

Developing, debugging, and testing Celery tasks can be more challenging than writing synchronous code. Efforts will be made early to simplify these things. Where possible, shared code will handle things like logging, tracing, and testing tasks. When not possible, thorough documents will be written explaining how to do the different things necessary to develop and administer these tasks.

Regarding code location, an extension may live in a Github repository external to Commerce Coordinator, but should have the code for all related API endpoints and Celery tasks that it manages inside that repository. This allows releasing all related code together at roughly the same time, even though the services are running in different processes.
