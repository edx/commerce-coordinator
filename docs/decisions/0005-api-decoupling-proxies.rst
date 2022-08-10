##########################
0005 API Decoupling Proxy
##########################

Status
******

**Draft**

Context
*******

We are working on the first step of the `overall deprecation plan <https://discuss.openedx.org/t/deprecation-removal-ecommerce-service-depr-22/6839#roadmap-3>`__:
- Decouple legacy ecommerce service from other systems by routing data through the Coordinator.
- Integrate Coordinator with new back-end systems and migrate processes as piecemeal as we can.
- Once nothing relies on the legacy integrations anymore, we can fully retire legacy ecommerce.

This "decoupling" work is important for enabling smooth, risk-managed, migration to new backend services not only for edX.org's installation, but as a ramp for other Open edX deployments implementing their own Commerce Coordinator integrations as well.

To start decoupling the legacy ecommerce service from other services and micro-frontends we’re building thin shims for the Coordiator and routing requests there and, for now, these shims will basically call the relevant legacy APIs.

Decision
********

Use a proxy pattern when interposing Coordinator in front of other services' APIs, particularly while decoupling the legacy ecommerce service.

Note: Commerce Coordinator should be used to facilitate coordination, especially _between_ systems involved in the order management workflow. It does not have to be added into the middle of every step.

Consequences
************

- Proxies can be brittle.
- Could consider caching at times but beware of the added complexity vs. how often the cached value might be used.
- Proxy pattern is primarily for, but not necessarily limited to, decoupling; there could be cases where this is the best pattern for routing and / or data transformation between systems.

When and How to Use a Decoupling Proxy
**************************************

*(( TODO: when to use decoupling proxy ))*

Managing Decoupling and Migration
=================================

- Build a pair of decoupling plugins for Coordinator
- Add a waffle flag _in the legacy system_ to manage the transition to routing through the Coordinator
- Test and roll-out Coordinator routing
- Write a Coordinator back-end plugin for the new system
- Add a Coordinator waffle flag
- Test and roll-out the new plugin / configuration

Author Concerns
***************

- Although directly proxying APIs is not generally intended to be a long-term solution, transition periods can stretch on longer than expected.  However, long-term reliance on the legacy ecommerce service is, in itself, a much greater concern than continuing to proxy any of its APIs.
- Decoupling the legacy ecommerce service by interposing the Coordinator could be misunderstood to mean that everything should continue to be routed through it.  The Coordinator does not have to broker all-the-things; systems-of-record can vend or host their own ui/frontends and other things that don't need to interact with anything else.

Alternatives Considered
***********************

Replication of business objects or functionality
================================================

- This would add significant complexity, requiring replication and synchronization processes for each type of data being duplicated.
- One argument for replication is to guard against failure in the source-of-truth legacy system; currently the legacy system is already a potential point-of-failure, it is the Coordinator that is a new possible failure point and obviously replication doesn't help with that.

Caching of results
==================

- Likely to be better than full replication, but it would also add significant complexity, requiring storage of the responses or response data and invalidation or refresh policies.
- Many APIs/responses have a low likelihood of reuse, for example caching an individual learner's order history.
- If an API *seems* like a good candidate for caching, test and profile first; err on the side of simplicity.
