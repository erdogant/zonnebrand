Examples
########

All examples below assume that your ``.secrets/keys`` file contains valid
``SUNNY_USERNAME``, ``SUNNY_PASSWORD``, and (optionally) ``RESEND_API_KEY``
values.  See :doc:`Installation` for credential setup.


Command-line interface
######################

``zonnebrand.py`` exposes a rich CLI.  Run ``--help`` to see all options:

.. code-block:: console

    python zonnebrand.py --help

Normal price-based control loop
********************************

Runs the continuous control loop.  Prices are refreshed once per day; the
export limit is re-evaluated every 15 minutes.

.. code-block:: console

    python zonnebrand.py

Use a specific energy provider
*******************************

By default the raw EPEX spot price is used.  Pass ``--provider`` to include
the markup of your own energy supplier (e.g. Zonneplan, ANWB, Tibber):

.. code-block:: console

    python zonnebrand.py --provider zonneplan
    python zonnebrand.py --provider tibber
    python zonnebrand.py --provider anwb

Supported provider names: ``all_in_power``, ``anwb``, ``budget``,
``coolblue``, ``delta``, ``easyenergy``, ``eneco``, ``vanons``,
``energiedirect``, ``energiek``, ``energyzero``, ``engie``, ``essent``,
``frank``, ``groenelokaal``, ``nextenergy``, ``oxxio``, ``powerpeers``,
``tibber``, ``vandebron``, ``vattenfall``, ``vrijopnaam``, ``zonneplan``.

Fetch and print today's price data
************************************

Fetches prices and prints all 96 quarter-hour slots to the console, then exits.

.. code-block:: console

    python zonnebrand.py --data
    python zonnebrand.py --data --provider zonneplan

Plot the price chart
********************

Opens an interactive Plotly chart in your browser showing inkoop, belasting,
and the total price per quarter-hour slot.

.. code-block:: console

    python zonnebrand.py --plot
    python zonnebrand.py --plot --provider anwb

Force a specific export limit
*******************************

Sets the export limit to an exact percentage and exits immediately, bypassing
all price-based logic.  Useful for manual overrides or testing.

.. code-block:: console

    python zonnebrand.py --set 0     # disable export
    python zonnebrand.py --set 100   # restore full export

Send status e-mails (Resend)
*****************************

Pass a recipient address with ``--mail``.  Requires ``RESEND_API_KEY`` in
your ``.secrets/keys`` file.

.. code-block:: console

    python zonnebrand.py --mail your@email.com

Debug with a visible browser window
*************************************

By default the browser runs headless.  Use ``--browser`` to watch every
Playwright step in a real browser window — handy when troubleshooting
ennexOS login issues.

.. code-block:: console

    python zonnebrand.py --browser

Combine multiple options
*************************

Options can be freely combined:

.. code-block:: console

    python zonnebrand.py --provider zonneplan --plot --mail your@email.com
    python zonnebrand.py --provider anwb --browser --mail your@email.com


Python API
##########

Quickstart
**********

.. code-block:: python

    from zonnebrand import Zonnebrand
    import os
    from dotenv import load_dotenv

    load_dotenv(".secrets/keys")

    client = Zonnebrand(
        username=os.getenv("SUNNY_USERNAME"),
        password=os.getenv("SUNNY_PASSWORD"),
    )

    # Start the continuous control loop (blocks forever)
    client.run()

Use a specific energy provider
*******************************

.. code-block:: python

    from zonnebrand import Zonnebrand
    import os
    from dotenv import load_dotenv

    load_dotenv(".secrets/keys")

    client = Zonnebrand(
        username=os.getenv("SUNNY_USERNAME"),
        password=os.getenv("SUNNY_PASSWORD"),
        provider="zonneplan",   # include Zonneplan markup in prices
    )

    client.run()

Fetch and inspect price data
*****************************

.. code-block:: python

    from zonnebrand import Zonnebrand

    client = Zonnebrand(provider="api")

    # Returns a list of dicts: [{date, time, price, provider}, ...]
    data = client.fetch_epex()

    for row in data[:5]:
        print(row)
    # {'date': '2026-05-09', 'time': '00:00', 'price': 0.263, 'provider': 'api'}

    # Fetch prices for a specific date
    data = client.fetch_epex(date="2026-05-01")

Check current price decision
*****************************

``decide_target`` returns the export-limit percentage (0 or 100) and a
human-readable reason string based on the current price slot.

.. code-block:: python

    from zonnebrand import Zonnebrand

    client = Zonnebrand(provider="api")
    data   = client.fetch_epex()

    target_perc, reason = client.decide_target(data)
    print(f"Target: {target_perc}%  |  Reason: {reason}")
    # Target: 0%  |  negative window 13:00-15:00 (120 min), price -0.1543 €/kWh

Plot the price chart
********************

.. code-block:: python

    from zonnebrand import Zonnebrand

    client = Zonnebrand(provider="zonneplan", showplot=True)
    data   = client.fetch_epex()   # also triggers the plot when showplot=True

    # Or plot explicitly after fetching:
    client.plot_chart()

Force-set the export limit
***************************

Directly writes the value to both SMA parameters via Playwright without going
through the price-decision logic.

.. code-block:: python

    import os
    from dotenv import load_dotenv
    from zonnebrand import Zonnebrand

    load_dotenv(".secrets/keys")

    client = Zonnebrand(
        username=os.getenv("SUNNY_USERNAME"),
        password=os.getenv("SUNNY_PASSWORD"),
    )

    client.set_sma_parameters(0)    # disable export
    client.set_sma_parameters(100)  # restore export

Run with e-mail notifications
*******************************

.. code-block:: python

    import os
    from dotenv import load_dotenv
    from zonnebrand import Zonnebrand

    load_dotenv(".secrets/keys")

    client = Zonnebrand(
        username=os.getenv("SUNNY_USERNAME"),
        password=os.getenv("SUNNY_PASSWORD"),
        provider="zonneplan",
        to_mail="your@email.com",
        resend_api_key=os.getenv("RESEND_API_KEY"),
    )

    client.run()

Run with visible browser (debug mode)
***************************************

.. code-block:: python

    import os
    from dotenv import load_dotenv
    from zonnebrand import Zonnebrand

    load_dotenv(".secrets/keys")

    client = Zonnebrand(
        username=os.getenv("SUNNY_USERNAME"),
        password=os.getenv("SUNNY_PASSWORD"),
        browser=True,       # show the Chromium window
        screenshot=True,    # save PNG screenshots at each step
    )

    client.set_sma_parameters(100)

Use built-in example data (no internet required)
*************************************************

A built-in day's price profile is available for offline testing.  It contains
a realistic negative-price window between 13:00 and 15:00.

.. code-block:: python

    from zonnebrand import Zonnebrand

    client = Zonnebrand(provider="example")
    data   = client.fetch_epex()

    target_perc, reason = client.decide_target(data)
    print(target_perc, reason)

Fetch prices via the stroomperuur.nl JSON API directly
*******************************************************

.. code-block:: python

    from zonnebrand import fetch_stroomperuur

    # Raw EPEX spot price (no provider markup)
    rows = fetch_stroomperuur(provider="api")

    # With a provider markup
    rows = fetch_stroomperuur(provider="zonneplan", date="2026-05-09")

    print(rows[0])
    # {'date': '2026-05-09', 'time': '00:00', 'price': 0.27345,
    #  'inkoop': 0.11234, 'belasting': 0.16111}


.. include:: add_bottom.add