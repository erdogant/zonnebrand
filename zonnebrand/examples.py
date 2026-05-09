# %%
# from zonnebrand import Zonnebrand
# client = Zonnebrand()
# client.messages()

# from sendmail import send_html_email
# send_html_email(to="test@test.com", subject="zonnebrand!", html="<h1>Bon voyage!</h1>")


# %% Plot epex from file
from zonnebrand import Zonnebrand

# Initialize
client = Zonnebrand()
client.plot_chart()
client.plot_chart('file')


# %% Fetch data
from zonnebrand import Zonnebrand
# Initialize

client = Zonnebrand(provider='zonneplan')
data = client.fetch_epex()
client.plot_chart()

# %% Plot from file
from zonnebrand import Zonnebrand

# Initialize
client = Zonnebrand(provider='api')
# Plot saved EPEX data
client.plot_chart(retrieve_data='file')
# Plot most current EPEX data
client.plot_chart(retrieve_data='current')

# %% Example data
from zonnebrand import Zonnebrand

# Initialize
client = Zonnebrand(provider='example')
# Get example data
data = client.example_data()

# %% Retrieve EPEX data from API
from zonnebrand import Zonnebrand

# Initialize
client = Zonnebrand(provider='api')
# Show chart
client.plot_chart()

# %% Retrieve EPEX data from provider
from zonnebrand import Zonnebrand

# Initialize
client = Zonnebrand(provider='zonneplan')
# Show chart
client.plot_chart()

# %% Set zonnebrand parameters based on positive-and-negative price changes
from dotenv import load_dotenv
import os

# Retrieve login from secrets
load_dotenv(".secrets/keys")
USERNAME = os.getenv("SUNNY_USERNAME")
PASSWORD = os.getenv("SUNNY_PASSWORD")

# Load library
from zonnebrand import Zonnebrand

# Initialize
# client = Zonnebrand(username=USERNAME, password=PASSWORD, provider='api')
client = Zonnebrand(username=USERNAME, password=PASSWORD, provider='zonneplan')
# Run and set parameters
client.run()

