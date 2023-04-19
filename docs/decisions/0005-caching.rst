############################
0005 Caching
############################

Status
******

**Draft**

Context
*******

Commerce Coordinator is a broker for network calls to other services. Network calls to other services are expensive (e.g. time-consuming). We want to introduce caching to remove unwanted network calls to other services and improve response time.

Decisions
*********

Caching introduces a fair amount of complexity. Use caching in Coordinator only for endpoints where we expect a large volume of responses.

Backend
-------
Coordinator will use `LocMemCache`_ for development and `PyMemcacheCache`_ for production.

Use PyMemcacheCache instead of MemcachedCache because it is now deprecated as of Django 3.2. See deprecation notice on Django's `Memcache`_ documentation.

Use PyMemcacheCache instead of PyLibMCCache because seems to be more used and is pure Python, and is faster and better maintained. See `this discussion`_.

.. _`LocMemCache`: https://docs.djangoproject.com/en/3.2/topics/cache/#local-memory-caching
.. _`PyMemcacheCache`: https://docs.djangoproject.com/en/3.2/topics/cache/#memcached
.. _`Memcache`: https://docs.djangoproject.com/en/3.2/topics/cache/#memcached
.. _`this discussion`: https://github.com/mozilla/addons-server/issues/16489

Expiration
----------
Use a default cache expiration time of 30 minutes. This is roughly the length of our average user payment checkout session.

Wrapper Functions
-----------------
Use ``TieredCache`` and ``get_cache_key`` from ``edx_django_utils.cache``. See `documentation`_.

Create wrapper functions around edx_django_utils.cache functions in Coordinator's core app.

Only use these cache wrapper functions to use the cache from Coordinator's other apps. This will help us centrally organize Coordinator's caching.

.. _`documentation`: https://github.com/openedx/edx-django-utils/tree/master/edx_django_utils/cache

Versioning
----------

Prefer versioned cache keys instead of overwriting existing cache entries. This will prevent accidental overwrites.

For example, instead of constantly overwriting ``payment.<payment_number>`` every time the state of a payment changes, prefer creating a cache entry for each state, like ``payment.<payment_number>.<state_name>``.

Consequences
************

Wrapper Functions
-----------------

..
    Add example of how to use wrapper functions here.

Versioning
----------

Avoid overwriting cache entries. When overwriting, add a comment as to why overwriting is necessary.
