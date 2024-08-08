8. Pull Commerce Coordinator related code out of edx-platform
#############################################################

Status
******

**Draft**

Context
*******

Kyle from Axim marked Commerce Coordinator related code in edx-platform as `business-related`. For Reference see `PR`_

.. _PR: https://github.com/openedx/edx-platform/pull/35203

As a result of this we need to pull out all the references of `commerce-coordinator` from `edx-platform` while also find a way to override the `edx-platform` code from our tooling to ensure that `commerce-coordinator` functionality remains intact.

Decision
********

We have decided to use `Django App Plugins`_ from `edx_django_utils`_ to override the `commerce-coordinator` related code in `edx-platform`. These plugins provide a way to override the application code without modifying the original codebase.
Specifically we will be using the `pluggable_overrides`_ which were designed to override any method to point to an alternate implementation.
As a result of this we will be able to pull out the `commerce-coordinator` related code from `edx-platform` and still be able to use the functionality provided by `commerce-coordinator`.

Separately we have decided to create a new pluggable application that will house all the `commerce-coordinator` related code that will be used to override the `edx-platform` code. This new pluggable application will be installed with `EDXAPP_PRIVATE_REQUIREMENTS`_ from `edx-internal`_.

.. _Django App Plugins: https://github.com/openedx/edx-django-utils/tree/master/edx_django_utils/plugins#django-app-plugins
.. _edx_django_utils: https://github.com/openedx/edx-django-utils
.. _pluggable_overrides: https://github.com/openedx/edx-django-utils/blob/master/edx_django_utils/plugins/pluggable_override.py
.. _EDXAPP_PRIVATE_REQUIREMENTS: https://github.com/edx/edx-internal/blob/master/ansible/vars/edx.yml#L38
.. _edx-internal: https://github.com/edx/edx-internal/

Rejected Alternatives
*********************

A lengthy R&D was undertaken to look at several options for pulling out the commerce coordinator related code from `edx-platform`.

Alternatives that were investigated and rejected:

- Using EduNext's Ecommerce extension
    - Rejected due to:
        - The extension solely deals with adding more payment gateways to the ecommerce ecosystem.
        - The extension does not provide a way to override the existing code blocks in `edx-platform`.
        - The extension is not actively maintained.
- Generic Flag names in edx-platform
    - Rejected due to:
        - This approach is not scalable.
        - This approach will not provide a way to override the existing code blocks in `edx-platform`.
