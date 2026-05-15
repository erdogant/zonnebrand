Installation
############

``zonnebrand`` requires **Python 3.10 or higher** and uses
`Playwright <https://playwright.dev/python/>`_ for browser automation to control
the SMA ennexOS portal.


Dependencies
************

The following packages are installed automatically via ``pip``:

* ``playwright`` — browser automation for ennexOS login and parameter setting
* ``plotly`` — interactive price charts
* ``requests`` — price-data API calls
* ``python-dotenv`` — credential loading from ``.secrets``
* ``resend`` *(optional)* — e-mail status notifications

After installing the package, you must also install the Playwright browser binaries once:

.. code-block:: console

    playwright install chromium


Credentials
***********

Create a file called ``.secrets/keys`` (or ``.secrets``) in your project root
with your SMA ennexOS credentials and — optionally — a Resend API key for
e-mail notifications:

.. code-block:: ini

    SUNNY_USERNAME=your_ennexos_email@example.com
    SUNNY_PASSWORD=your_ennexos_password
    RESEND_API_KEY=re_xxxxxxxxxxxxxxxxxxxx   # optional


----

Install from PyPI
*****************

.. code-block:: console

    # Install from PyPI:
    pip install zonnebrand

    # Force update to the latest version:
    pip install -U zonnebrand

    # Install Playwright browser binaries (required once):
    playwright install chromium


Install from GitHub
*******************

.. code-block:: console

    # Install the latest development version directly from GitHub:
    pip install git+https://github.com/erdogant/zonnebrand


Create a Conda environment
**************************

.. code-block:: console

    conda create -n env_zonnebrand python=3.12
    conda activate env_zonnebrand
    pip install zonnebrand
    playwright install chromium


Create a venv environment
*************************

.. code-block:: console

    # Create a new project directory
    mkdir my_zonnebrand_project
    cd my_zonnebrand_project

    # Create virtual environment
    python -m venv venv

    # Activate (macOS / Linux):
    source venv/bin/activate

    # Activate (Windows):
    venv\Scripts\activate

    # Install
    pip install zonnebrand
    playwright install chromium


Docker
######

A ``docker-compose.yml`` is included in the repository so you can run
zonnebrand as a persistent background service without touching your local
Python environment.

Build and start (first time)
*****************************

.. code-block:: console

    docker compose up -d --build

Start an existing container
***************************

.. code-block:: console

    docker compose up -d

Inspect running containers
**************************

.. code-block:: console

    docker ps
    docker image ls

View live logs
**************

.. code-block:: console

    docker compose logs -f

Clean up unused resources
*************************

.. code-block:: console

    docker system prune
    docker builder prune
    docker rm -f <container_id>


Uninstalling
############

Remove the package
******************

.. code-block:: console

    pip uninstall zonnebrand

Remove a Conda environment
**************************

.. code-block:: console

    # List active environments (zonnebrand should appear):
    conda env list

    # Remove the environment:
    conda env remove --name env_zonnebrand

    # Verify removal:
    conda env list


.. include:: add_bottom.add