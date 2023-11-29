7. SDN Sancationed State on Orders in Commercetools for R0.1
############################################################

Status
******

**Provisional** *2023-11-29* -- R0.1

Context
*******

Due to the speed required for R0.1, we needed a way to mark orders as blocked by an SDN match.

This will be implemented by a single `custom State`_ within the Order. This is sometimes referred to as a [Workflow] Transition State.

.. _custom State: https://docs.commercetools.com/api/projects/states

Decision
********

This has lead to the creation of the following is the CoCo State definition:

.. code-block:: python

    SANCTIONED_ORDER_STATE = StateDraft(
        key=TwoUKeys.SDN_SANCTIONED_ORDER_STATE,
        type=StateTypeEnum.ORDER_STATE,
        name=ls({'en': 'Sanctioned'}),
        description=ls({'en': 'This order has been sanctioned for an SDN hit'})
    )


Consequences
************

Workflow states are not easily viewed via the Merchant Center UI as there is no universal listing of aall states within the system. However we do have some support scripts to help view a master list given a certain CoCo endpoint and key.

Rejected Alternatives
*********************

We could have used custom objects and their fields to implement this, however there is a universal wish to avoid adding too much custom data. It was decided by the Sonic leads that this would be the simplest solution.
