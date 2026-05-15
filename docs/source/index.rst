zonnebrand — Solar panel export-limit controller for SMA inverters
===================================================================

.. container:: logo-description

   .. image:: ../figs/logo.png
      :width: 125px
      :height: 125px
      :align: left
      :alt: zonnebrand logo

   **zonnebrand** is a Python tool that automatically protects your SMA solar inverter
   during negative electricity price windows. It monitors real-time EPEX spot prices
   and adjusts the two export-limit
   parameters in ennexOS to **0 %** when prices go negative and restores them to
   **100 %** when prices recover — fully automated, every 15 minutes.

   .. raw:: html

      <div style="clear: both;"></div>


-----------------------------------

.. |python| image:: https://img.shields.io/pypi/pyversions/zonnebrand.svg
    :alt: Python versions
    :target: https://erdogant.github.io/zonnebrand/

.. |pypi| image:: https://img.shields.io/pypi/v/zonnebrand.svg
    :alt: PyPI version
    :target: https://pypi.org/project/zonnebrand/

.. |docs| image:: https://img.shields.io/badge/Sphinx-Docs-Green.svg
    :alt: Sphinx documentation
    :target: https://erdogant.github.io/zonnebrand/

.. |LOC| image:: https://sloc.xyz/github/erdogant/zonnebrand/?category=code
    :alt: Lines of code
    :target: https://github.com/erdogant/zonnebrand

.. |downloads_month| image:: https://static.pepy.tech/personalized-badge/zonnebrand?period=month&units=international_system&left_color=grey&right_color=brightgreen&left_text=PyPI%20downloads/month
    :alt: Downloads per month
    :target: https://pepy.tech/project/zonnebrand

.. |downloads_total| image:: https://static.pepy.tech/personalized-badge/zonnebrand?period=total&units=international_system&left_color=grey&right_color=brightgreen&left_text=Downloads
    :alt: Downloads in total
    :target: https://pepy.tech/project/zonnebrand

.. |license| image:: https://img.shields.io/badge/License-GPLv3-blue.svg
    :alt: License
    :target: https://www.gnu.org/licenses/gpl-3.0

.. |forks| image:: https://img.shields.io/github/forks/erdogant/zonnebrand.svg
    :alt: Github Forks
    :target: https://github.com/erdogant/zonnebrand/network

.. |open issues| image:: https://img.shields.io/github/issues/erdogant/zonnebrand.svg
    :alt: Open Issues
    :target: https://github.com/erdogant/zonnebrand/issues

.. |project status| image:: http://www.repostatus.org/badges/latest/active.svg
    :alt: Project Status
    :target: http://www.repostatus.org/#active

.. |donate| image:: https://img.shields.io/badge/Support%20this%20project-grey.svg?logo=github%20sponsors
    :alt: Donate
    :target: https://erdogant.github.io/zonnebrand/pages/html/Documentation.html#

|python| |pypi| |docs| |LOC| |downloads_month| |downloads_total| |license| |forks| |open issues| |project status| |donate|

-----------------------------------

Support
-------

.. raw:: html

    <div style="display: flex; align-items: center; gap: 20px;">
        <iframe
            srcdoc='<a href="https://www.buymeacoffee.com/erdogant" target="_blank"><img src="https://img.buymeacoffee.com/button-api/?text=Buy me a coffee&amp;emoji=&amp;slug=erdogant&amp;button_colour=FFDD00&amp;font_colour=000000&amp;font_family=Cookie&amp;outline_colour=000000&amp;coffee_colour=ffffff" /></a>'
            style="border:none; width:250px; height:80px; flex-shrink: 0;">
        </iframe>
        <div>
            <p><strong>Yes! This library is entirely free but it runs on coffee.</strong>
            Your ❤️ is important to keep maintaining this package. You can
            <a href="https://erdogant.github.io/zonnebrand/pages/html/Documentation.html">support</a>
            in various ways — have a look at the
            <a href="https://erdogant.github.io/zonnebrand/pages/html/Documentation.html">sponsor page</a>.</p>
        </div>
    </div>

-----------------------------------

Quick install
-------------

.. code-block:: console

    pip install zonnebrand


.. code-block:: console

    zonnebrand <enter>
    sunscreen <enter>


Run directly using python

.. code-block:: console

    python zonnebrand.py --provider zonneplan --mail your_mail@gmail.com

-----------------------------------


Contents
========

.. toctree::
   :maxdepth: 2
   :caption: Getting started

   Installation

.. toctree::
   :maxdepth: 1
   :caption: Server

   server

.. toctree::
   :maxdepth: 1
   :caption: Examples

   Examples

.. toctree::
   :maxdepth: 2
   :caption: Documentation

   Documentation
   Dashboard
   zonnebrand.zonnebrand


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`


.. include:: add_bottom.add