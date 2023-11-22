6. Commercetools Customer Lookup for R0.1
#########################################

Status
******

**Provisional** *2023-11-13* -- R0.1

Context
*******

Due to the speed required for R0.1, we had to implement a simple but immediate implementation for the management of Customer objects in Commcercetools Composable Commerce ("CoCo").

This will be implemented by a single `Custom Type`_ attached to the Customers tagged for R0.1 as an edX User.

.. _Custom Type: https://docs.commercetools.com/api/projects/types

Decision
********

This has lead to the creation of the following is the CoCo type definition:

.. code-block:: python

    CUSTOMER_TYPE_DRAFT = TypeDraft(
        key='2u-user_information',
        name=ls({'en': '2U Cross System User Information'}),
        resource_type_ids=[ResourceTypeId.CUSTOMER],
        description=ls({'en': '2U Cross System User Information, shared among all LOBs and '
                              'by various LMS and backend systems.'}),
        # ^^^ this cannot be updated, the whole type has to be unassigned, removed and replaced.
        field_definitions=[
            FieldDefinition(
                type=CustomFieldStringType(),
                name='edx-lms_user_id',
                required=False,
                label=ls({'en': 'edX LMS User Identifier'}),
                input_hint=TypeTextInputHint.SINGLE_LINE
            ),
            FieldDefinition(
                type=CustomFieldStringType(),
                name='edx-lms_user_name',
                required=False,
                label=ls({'en': 'edX LMS User Name'}),
                input_hint=TypeTextInputHint.SINGLE_LINE
            )
        ]
    )

This type definition allows us to add the LMS User ID, and LMS Username to be attached to a Customer record in CoCo.

 ===================== ======== =================================================================================================================================================================
  Field Name            Type     Description
 ===================== ======== =================================================================================================================================================================
  `edx-lms_user_id`     String   While this is an integer for future proofing and `safe value handling`_ via the API this is a String. Coordinator uses this value for most (but not all) calls.
  `edx-lms_user_name`   String   This is used by Order History conversion and possibly in the future by enrollment in LMS.
 ===================== ======== =================================================================================================================================================================

.. warning::
    The use of `safe value handling`_ is currently limited to String values only.

.. _safe value handling: https://docs.commercetools.com/api/predicates/query#input-variables

Consequences
************

Updates to custom types have some note pain points. The following are from a conversation with Commercetools:

Question:

 Custom Types, if we choose to map a field to another, is there a simple way to perform a broad data migration. For example if we want to change a custom type attached to a Customer, is there a way to do this in bulk. The idea that we have to fetch a Customer via an API, attach a new type, migrate its custom fields and update the Customer Object's Custom Type with the modified fields?

 For example if we decide a data type has to change, from Integer to String or vice versa? In theis case there is no automated way to change a field type, so we have to decide to add a new one, and update all the objects, then modify all systems to try and read from that new field.... If it needs to cange in place, we need to create a duplicate type, and swap out...

 We are hoping for a more modern 'Migration script' type system as one would write in Ruby or Python to alter a Datatable in a Database.

Here is the formal response from Commercetools:

 The type can be defined and changed using the labd terraform provider - `labd/terraform-provider-commercetools`_

 The provider doesn't handle moving the data values but rather just the definition and manipulation of the schema / configuration. It is recommended to add the new attribute definition(s), move the values, then remove the old attributes.

.. _labd/terraform-provider-commercetools: https://registry.terraform.io/providers/labd/commercetools/latest/docs

Rejected Alternatives
*********************

Custom Objects can be created with references to a Customer by ID. Which can then be pulled via expansion in the API. However, this has some limits of total custom objects in the whole system as well as low lookups when the volume of objects gets high. There are a potential (not filtered by enterprise or staff status) of 52,998,345 in the current database of LMS in production. The `limit for Custom Objects`_ is 20,000,000 for the entire organization, not limited to the edX Line of Business. Which is 2.6x the count available in total.

.. _limit for Custom Objects: https://docs.commercetools.com/api/limits?#custom-objects
