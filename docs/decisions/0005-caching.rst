############################
0005 Caching
############################

Status
******

**Draft**

Context
*******

The Commerce Coordinator is significantly a broker for network calls to other services.
Network calls to other services are expensive (e.g. time-consuming).
We want to introduce caching to remove unwanted network calls to other services and improve response time.

Decisions
*********
- This application will use **Local-memory caching** for development and **Memcached** for production.
- Default cache expiration time should be 30 Minutes.
- Caching utilities will be placed in core app utils. As these utils will be used by all apps and we want to avoid circular dependency.
- Application will make good use of ``TieredCache`` and ``get_cache_key`` from ``edx_django_utils.cache``
- Caching keys having versions will be preferred over resetting existing keys to maintain multiple state objects. (For example, Payment Processing and Paid state). It will avoid the chances of overriding the wrong states accidentally.

Consequences
************

Developing, debugging, and testing can be more challenging for tasks with caching.
Sequence diagrams will be added to explain complex caching flows.
Efforts will be made early to simplify these things. Where possible, shared code will handle things like logging, tracing, and testing tasks.
