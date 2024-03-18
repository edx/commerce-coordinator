Using Ngrok
###########

Commerce Coordinator was built to connect Open edX and non-Open-edX services.
Non-Open-edX services may be cloud-hosted, and not reside on a developer's
local machine.

This How To walks through using a service called `Ngrok`_ to generate URLs for
a cloud service to connect to an Open edX service located on a developer's
local machine for testing and development purposes.

.. _Ngrok: https://ngrok.com

#. Start LMS in devstack at http://localhost:18000.

#. Start Coordinator on your local at http://localhost:8140.

#. Create an Ngrok account and get an authtoken at
   https://dashboard.ngrok.com/get-started/your-authtoken

#. Coordinator's repo has file ngrok.yml. Run from the same directory as
   ngrok.yml. Substitute your Ngrok authtoken from step above.

    .. code-block::

        brew install ngrok/ngrok/ngrok
        ngrok config add-authtoken --config ngrok.yml <AUTHTOKEN>
        ngrok start --config ngrok.yml --all

#. You should see the urls for Coordinator and LMS Ngrok appear in your
   console, similar to:

    .. code-block::

        https://032f-2601-184-497f-983e-20b0-ed78-ed2f-6f.ngrok-free.app → http://localhost:8140
        https://852e-2601-184-497f-983e-20b0-ed78-ed2f-6f.ngrok-free.app → http://localhost:18000
