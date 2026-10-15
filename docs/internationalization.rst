.. _chapter-i18n:

Internationalization
####################
All user-facing text content should be marked for translation. Even if this application is only run in English, our
open source users may choose to use another language. Marking content for translation ensures our users have
this choice.

Follow the `internationalization coding guidelines`_ in the edX Developer's Guide when developing new features.

.. _internationalization coding guidelines: https://edx.readthedocs.org/projects/edx-developer-guide/en/latest/internationalization/i18n.html

Updating Translations
*********************
This project follows `OEP-58`_. Translations are not stored in this repository. They live in the
`edx/openedx-translations`_ repository and are downloaded with the `openedx-atlas`_ CLI (``atlas``).

.. _OEP-58: https://docs.openedx.org/en/latest/developers/concepts/oep58.html
.. _edx/openedx-translations: https://github.com/edx/openedx-translations
.. _openedx-atlas: https://github.com/openedx/openedx-atlas

Source strings do not need to be pushed. A daily GitHub Actions workflow in edx/openedx-translations checks out this
repository, runs ``make extract_translations`` and commits the English source files (``django.po`` and
``djangojs.po``). The translations for each language are then generated in edx/openedx-translations by the
ai-translations service.

``make pull_translations`` removes every language directory under ``commerce_coordinator/conf/locale``, downloads the
translation files with ``atlas pull`` and compiles them. ``atlas`` pulls from ``openedx/openedx-translations`` by
default, which does not have this project's translations, so set ``ATLAS_OPTIONS`` when you run it locally::

    ATLAS_OPTIONS=--repository=edx/openedx-translations make pull_translations

The ``make`` targets listed below are used in this process.

..  list-table::
    :widths: 25 75
    :header-rows: 1

    * - Target
      - Description
    * - extract_translations
      - Extract strings marked for translation into the English source files
    * - pull_translations
      - Pull translations from edx/openedx-translations with ``atlas`` and compile them

Fake Translations
*****************
As you develop features it may be helpful to know which strings have been marked for translation, and which are not.
Use the `fake_translations` make target for this purpose. This target will extract all strings marked for translation,
generate fake translations in the Esperanto (eo) language directory, and compile the translations.

You can trigger the display of the translations by setting your browser's language to Esperanto (eo), and navigating to
a page on the site. Instead of plain English strings, you should see specially-accented English strings that look
like this:

    Thé Fütüré øf Ønlïné Édüçätïøn Ⱡσяєм ι# Før änýøné, änýwhéré, änýtïmé Ⱡσяєм #

