####################
commerce-coordinator
####################

|pypi-badge| |ci-badge| |doc-badge| |pyversions-badge|
|license-badge| |status-badge|

A controller to manage commerce workflows and services

Overview
********

Commerce Coordinator is intended to be a highly decoupled, modular, asynchronous platform for handling a wide variety of use cases and workflows. In order to allow for flexibility in configuration and extensibility the Coordinator needs to have a loosely coupled internal architecture that allows for pluggable components to work with the same events.

Individual Django apps will act as plugins to implement specific functionality, for example a webhook for a payment service provider to call when a purchase is successful, that plugin can then signal one that performs the fulfillment in the LMS.

The core of the Coordinator will allow commerce workflows to be tailored by combining plugins and routing signals, and will eventually include tools for validating configurations and tracing signal flows.

For more details, please see the `architectural decision docs <docs/decisions>`_

Development Workflow
********************

Initial Setup: steps and confirmation
======================================

Note: this setup process is temporary; we will be working on a Tutor plugin

Local
======

.. code-block:: console

  # Clone the repository
  git clone git@github.com:edx/commerce-coordinator.git
  cd commerce-coordinator

  # if you wish to use a mysql daemon, install mysql, otherwise, start along with redis
  # brew install mysql

  # Set up a virtualenv and activate it
  python3 -m venv .venv
  source .venv/bin/activate

  # Install/update the dev requirements (run inside the venv)
  make requirements
  # If you get 'Unsupported architecture' errors above, instead use: CFLAGS='-D__x86_64__' make requirements

  # Expose the redis port for devstack (needed until commerce coordinator is part of devstack)
  # (redis is the backend that Celery is using for persisting the message queue)
  # In your local Devstack directory, edit docker-compose.yml: go to the redis service line and add a ports section
  # ports:
  #  - "6379:6379"

  # Start redis/mysql in devstack from your local devstack directory
  make dev.up.redis

  # If youd prefer to reuse mysql from devstack, start it now.
  # make dev.up.mysql57

  # Start ecommerce and lms in devstack from your local devstack directory
  make dev.up.ecommerce+lms

  # Return to the commerce-coordinator repo directory and provision credentials:
  bash local-provision-commerce-coordinator.sh

  # compile static assets
  python manage.py collectstatic

  # run commerce-coordinator locally (run inside the venv)
  python manage.py runserver localhost:8140 --settings=commerce_coordinator.settings.local

  # You should see output ending with "Quit the server with CONTROL-C"
  # In your browser, hit the URL: http://localhost:8140/demo_lms/test/
  # You should see JSON output indicating that two receivers were called, one successful, and one with exception/traceback information.
  # In the shell where the server is running you should see log output indicating that two test receivers were called with the sender argument "Something".

Local setup with Commercetools
===============================

1. Inside ``commerce_coordinator/settings/`` folder create a new file called ``private.py`` and copy the following:
    1. Copy the ``COMMERCETOOLS_CONFIG`` present in ``base.py`` to ``private.py`` and update with values found in Keeper under ``Shared-marketplace-commercetools`` with the name ``dev-commercetools-frontend API Key``
    2. Copy the ``PAYMENT_PROCESSOR_CONFIG`` present in ``base.py`` to ``private.py`` and update with the following values:
        - ``Stripe publishable_key`` and ``Stripe secret_key`` can be found at: https://dashboard.stripe.com/apikeys for ``edx Local/Dev`` account
        - ``Paypal client_id`` and ``Paypal client_secret`` can be found from Keeper under ``Shared-marketplace-commercetools`` with the name ``[PayPal-DEV] devstack-edx-commercetools-checkout``

2. Go to http://localhost:8140/admin/waffle/flag/ and add the following waffle flags:
        - ``transition_to_commercetools.redirect_to_commercetools_checkout`` flag with the **Everyone** attribute set to **Yes**.
        - ``transition_to_commercetools.order_fulfillment_service_forwarding_enabled`` flag with the **Everyone** attribute set to **Yes**.
        - ``transition_to_commercetools.program_redirect_to_commercetools_checkout`` flag with the **Everyone** attribute set to **Yes**.

3. Install and setup the ``edx-ecommerce-extension`` repo from the following link: https://github.com/edx/edx-ecommerce-extension

4. Setup the AWS Event Bridge to send events to the Commerce Coordinator using the `AWS EventBridge setup guide <https://2u-internal.atlassian.net/wiki/spaces/ER/pages/760054641/Connecting+Commerce+Tools+to+Coordinator+via+AWS+EventBridge#Testing-locally>`_

In case you run into issues while setting up the Commerce Coordinator, please refer to the `FAQ <>`_ for more details.

Every time you develop something in this repo
=============================================
.. code-block:: console

  # Grab the latest code
  git checkout main
  git pull

  # Activate the virtualenv
  source .venv/bin/activate

  # Install/update the dev requirements (run inside the venv)
  make requirements
  # If you get 'Unsupported architecture' errors above, instead use: CFLAGS='-D__x86_64__' make requirements

  # Make a new branch for your changes
  git checkout -b <your_github_username>/<short_description>

  # Start redis and the webserver as in previous section

  # Run the tests and quality checks (before and after your changes)
  make validate

  # Commit your changes
  git commit …
  git push

  # Open a PR and ask for review.


Local testing with Celery
=========================
.. code-block:: console

  # Start redis in devstack from your local devstack directory
  make dev.up.redis

  # Update the CELERY_BROKER_URL flag
  Update CELERY_BROKER_URL to "redis://:password@localhost:6379/0" inside `commerce_coordinator/settings/local.py`

  # Start celery from the commerce-coordinator venv; this management command will auto-reload celery when python files are changed
  python manage.py celery

  # More test URLs you can hit in the browser or pipe through jq (https://stedolan.github.io/jq/) to make the output more readable:
  curl -s "http://localhost:8140/demo_lms/test_celery_signal/" | jq '.'
  {
      "<function test_celery_signal_task at 0x10e17a9d0>": ""
  }

  curl -s "http://localhost:8140/demo_lms/demo_purchase_complete/" | jq '.'
  {
      "<function demo_purchase_complete_order_history at 0x10e18a430>": "",
      "<function demo_purchase_complete_send_confirmation_email at 0x10e18a5e0>": "",
      "<function demo_purchase_complete_enroll_in_course at 0x10e18a670>": ""
  }

With Docker (Not currently supported)
=====================================

As of the time of this writing, you must have run `make dev.up.ecommerce+lms+redis` in edX's devstack as a prerequisite to this one.

Execute `make dev.provision_docker`

This will attempt to connect to LMS and create the required superusers, please ensure you have the edX devstack setup first.

After you can manage the stack by calling `make dev.up`, `make dev.down` (delete) or `make dev.stop`.

License
*******

The code in this repository is licensed under the AGPL 3.0 unless
otherwise noted.

Please see `LICENSE.txt <LICENSE.txt>`_ for details.

Areas of concern/refinement
***************************

So far, this is very preliminary work proving out our ability to confirm and control Django signal / receiver mappings using the settings file. It is not yet a fully robust implementation, but is just a guidepost showing that our intended implementation can work.

Note: We expect that the system will be easier to reason about if signals are only confined to the primary IDA; other environments (e.g. Celery workers) could call API endpoints to trigger workflows if necessary.

How To Contribute
*****************

Contributions are very welcome.
Please read `How To Contribute <https://github.com/edx/edx-platform/blob/main/CONTRIBUTING.rst>`_ for details.  Even though they were written with ``edx-platform`` in mind, the guidelines should be followed for all Open edX projects.

The pull request description template should be automatically applied if you are creating a pull request from GitHub. Otherwise you can find it at `PULL_REQUEST_TEMPLATE.md <.github/PULL_REQUEST_TEMPLATE.md>`_.

The issue report template should be automatically applied if you are creating an issue on GitHub as well. Otherwise you can find it at `ISSUE_TEMPLATE.md <.github/ISSUE_TEMPLATE.md>`_.

Reporting Security Issues
*************************

Please do not report security issues in public. Please email security@edx.org.

Getting Help
************

If you're having trouble, we have discussion forums at https://discuss.openedx.org where you can connect with others in the community.

Our real-time conversations are on Slack. You can request a `Slack invitation`_, then join our `community Slack workspace`_.

For more information about these options, see the `Getting Help`_ page.

.. _Slack invitation: https://openedx-slack-invite.herokuapp.com/
.. _community Slack workspace: https://openedx.slack.com/
.. _Getting Help: https://openedx.org/getting-help

.. |pypi-badge| image:: https://img.shields.io/pypi/v/commerce-coordinator.svg
    :target: https://pypi.python.org/pypi/commerce-coordinator/
    :alt: PyPI

.. |ci-badge| image:: https://github.com/edx/commerce-coordinator/workflows/Python%20CI/badge.svg?branch=main
    :target: https://github.com/edx/commerce-coordinator/actions
    :alt: CI

.. |doc-badge| image:: https://readthedocs.org/projects/commerce-coordinator/badge/?version=latest
    :target: https://commerce-coordinator.readthedocs.io/en/latest/
    :alt: Documentation

.. |pyversions-badge| image:: https://img.shields.io/pypi/pyversions/commerce-coordinator.svg
    :target: https://pypi.python.org/pypi/commerce-coordinator/
    :alt: Supported Python versions

.. |license-badge| image:: https://img.shields.io/github/license/edx/commerce-coordinator.svg
    :target: https://github.com/edx/commerce-coordinator/blob/main/LICENSE
    :alt: License

.. |status-badge| image:: https://img.shields.io/badge/Status-Experimental-yellow
