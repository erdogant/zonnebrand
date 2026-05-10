Documentation
#############

.. include:: sponsor.rst


How it works
############

``zonnebrand`` runs a continuous loop that:

1. **Fetches daily price data** from API for specific providers.
   once per day (96 quarter-hour slots or 24 hourly slots, depending on the provider).
2. **Decides the export limit** by checking whether the current time slot has a
   negative electricity price.  Negative-price windows shorter than 5 minutes are
   ignored to avoid unnecessary toggling.
3. **Logs in to ennexOS** (SMA Sunny Portal) via a headless Chromium browser
   (Playwright) and sets both export-limit parameters
   (``Parameter.PCC.FlbInv.WMaxNom`` and ``Parameter.PCC.WMaxNom``) to
   **0 %** during negative prices and **100 %** otherwise.
4. **Sends a status e-mail** (via the Resend API) whenever the export limit changes.
5. **Sleeps for 15 minutes** and repeats.

All decisions and state changes are appended to ``dashboard/status.csv``; price
data is stored in ``dashboard/epex.csv``.


Configuration reference
########################

The ``Zonnebrand`` class accepts the following parameters:

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Parameter
     - Default
     - Description
   * - ``username``
     - ``None``
     - ennexOS account e-mail address (``SUNNY_USERNAME``).
   * - ``password``
     - ``None``
     - ennexOS account password (``SUNNY_PASSWORD``).
   * - ``provider``
     - ``'api'``
     - Price source: ``'api'`` for raw EPEX spot prices, or any supported
       energy-supplier name (e.g. ``'zonneplan'``, ``'tibber'``, ``'anwb'``).
   * - ``showplot``
     - ``False``
     - Open an interactive Plotly price chart in the browser after each
       daily price fetch.
   * - ``browser``
     - ``False``
     - Run Chromium in **visible** mode (``False`` = headless).
       Useful for debugging ennexOS login issues.
   * - ``screenshot``
     - ``False``
     - Save PNG screenshots at every Playwright step to the log directory.
   * - ``logdir``
     - ``'./dashboard/'``
     - Directory for ``status.csv`` and ``epex.csv`` log files.
       Use ``'tempdir'`` for the OS temp directory.
   * - ``resend_api_key``
     - ``None``
     - API key for the `Resend <https://resend.com>`_ e-mail service.
   * - ``to_mail``
     - ``None``
     - Recipient e-mail address for status-change notifications.


Supported energy providers
###########################

The following provider names can be passed to ``--provider`` (CLI) or the
``provider`` argument (Python API):

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Name
     - Notes
   * - ``api`` *(default)*
     - EPEX spot price.
   * - ``zonneplan``
     - Zonneplan dynamic tariff.
   * - ``tibber``
     - Tibber dynamic tariff.
   * - ``anwb``
     - ANWB Energie dynamic tariff.
   * - ``easyenergy``
     - EasyEnergy.
   * - ``vandebron``
     - Vandebron.
   * - ``energyzero``
     - EnergyZero.
   * - ``frank``
     - Frank Energie.
   * - ``vattenfall``
     - Vattenfall.
   * - ``essent``
     - Essent.
   * - ``eneco``
     - Eneco.
   * - ``coolblue``
     - Coolblue Energie.
   * - ``nextenergy``
     - NextEnergy.
   * - ``budget``
     - Budget Energie.
   * - ``groenelokaal``
     - Groene Lokaal.
   * - ``delta``
     - Delta.
   * - ``vrijopnaam``
     - Vrij op Naam.
   * - ``energiedirect``
     - EnergieDirect.
   * - ``energiek``
     - Energiek.
   * - ``engie``
     - Engie.
   * - ``powerpeers``
     - PowerPeers.
   * - ``oxxio``
     - Oxxio.
   * - ``vanons``
     - Van Ons.
   * - ``all_in_power``
     - All in Power.


Log files
#########

Two CSV files are written to ``logdir`` (default ``./dashboard/``):

``status.csv``
    One row per control decision with columns ``date``, ``time``,
    ``target_percent``, and ``reason``.

``epex.csv``
    One row per quarter-hour price slot with columns ``date``, ``time``,
    ``price``, and ``provider``.  Historical data accumulates across days
    (duplicates are de-duplicated on load).


GitHub
######

.. note::
    `Source code of zonnebrand can be found on GitHub <https://github.com/erdogant/zonnebrand/>`_


Citing
######

.. note::
    A BibTeX citation can be found on the right-hand side of the
    `GitHub page <https://github.com/erdogant/zonnebrand/>`_.


.. include:: add_bottom.add