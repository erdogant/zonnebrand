"""zonnebrand Controller
=====================================================

Name        : zonnebrand.py
Author      : E.Taskesen
github      : https://github.com/erdogant/zonnebrand
Licence     : GNU GENERAL PUBLIC LICENSE VERSION 3

"""

import asyncio
import time
import os
import re
import csv
import logging
import tempfile
import threading
import requests
from datetime import datetime, timezone, timedelta, date
from dotenv import load_dotenv
import plotly.graph_objects as go
from playwright.async_api import async_playwright, TimeoutError as PWTimeout

try:
    from sendmail import send_html_email
    SENDMAIL_FLAG = True
except:
    SENDMAIL_FLAG = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-7s  %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
logger = logging.getLogger(__name__)

# %%
class Zonnebrand():
    """zonnebrand."""

    def __init__(self, 
                 username=None,
                 password=None,
                 provider='api',
                 model='sma-sunny-tripower',
                 # showplot=False,
                 browser=False,
                 logdir='./dashboard/',
                 to_mail=None,
                 resend_api_key=None,
                 screenshot=False,
                 ):
        """Initialize zonnebrand with user-defined parameters.

        Parameters
        ----------
        provider : str
            Energy provider
            'api': Default
            'zonneplan', 'anwb', ...
            'example'

        Returns
        -------
        object.

        Examples
        --------
        >>> from zonnebrand import Zonnebrand
        >>> client = Zonnebrand(provider='zonneplan')
        >>> # Fetch data
        >>> client.fetch_epex()
        >>> # Plot chart
        >>> client.plot()
        >>> # Run
        >>> client.run()

        References
        ----------
            * https://erdogant.github.io/zonnebrand

        """
        self.username = username
        self.password = password
        self.provider=provider
        self.model = model
        # self.showplot = showplot
        self.browser = browser
        self.to_mail = to_mail
        self.resend_api_key = resend_api_key
        self.screenshot = screenshot
        
        # ignore negative-price slots shorter than this to avoid enable/disabling the solor panels
        self.MIN_WINDOW_MINUTES = 5

        # Re-evaluate prices every x seconds. Data is available for 15min interval.
        self.CHECK_INTERVAL_SECONDS = 60*15
        self.COUNTRY = 'NL'
        self.URL_STROOMPERUUR = "https://stroomperuur.nl/?kwartier=1"
        self.URL_MAIN = None
        self.set_logfile(logdir)
        
        # Check the allowed models
        allowed_models = ['sma-sunny-tripower']
        if self.model not in allowed_models:
            raise ValueError(f"Unsupported model: {self.model!r} Allowed models are: {allowed_models}")
        # Set the main page URL for SMA
        if self.model=='sma-sunny-tripower':
            self.URL_MAIN = "https://ennexos.sunnyportal.com/16879812,16879815/configuration/view-parameters"


    # =============================================================================
    # LOGFILES
    # =============================================================================
    def set_logfile(self, logdir):
        # 1) Resolve tempdir
        if logdir == "tempdir":
            logdir = os.path.join(tempfile.gettempdir())

        # 2) Normalize path: directory or file
        logdir = os.path.expanduser(logdir)
    
        # If user passed a directory only → append default filename
        logStatus = os.path.join(logdir, "status.csv")
        logEpex = os.path.join(logdir, "epex.csv")

        # 3) Ensure directory exists
        logdir = os.path.dirname(logStatus)

        # Create dir if required
        if logdir and not os.path.exists(logdir):
            os.makedirs(logdir, exist_ok=True)
            logger.info(f"Created directory: {logdir}")
    
        # 4) Create header if file does not exist
        append_log_data(logStatus)

        # 5) Store and show
        self.logfiles = {'status': logStatus, 'epex': logEpex, 'tempdir': logdir}
        logger.info(f"Logfiles: {self.logfiles}")
    

    # =============================================================================
    # MAIN LOOP
    # =============================================================================
    def run(self) -> None:
        logger.info("Zonnebrand shield started.")

        last_state: int | None = None
        cached_data = None
        cache_date = None
    
        # Resolve logfile path
        if self.logfiles:
            logger.info("Logging to: %s", self.logfiles['status'])
    
        while True:
            try:
                today = get_date_time(format_type='today_object')

                # Refresh once per day
                if cached_data is None or cache_date != today:
                    cached_data = self.fetch_epex()
                    cache_date = today
                    # Write EPEX prices to csv
                    append_epex_prices(self.logfiles['epex'], cached_data)
                    # Show plot
                    # if self.showplot: self.plot()
                    # Show debug info
                    logger.debug("Cached %d price slots", len(cached_data))

                # Decision logic
                target_perc, reason = self.decide_target(cached_data)
                
                # Set SMA parameters when needed
                if target_perc != last_state:
                    logger.info("State change → %d%% | %s", target_perc, reason)

                    # Make changes to SMA Sunny Tripower
                    if self.model=='sma-sunny-tripower':
                        self.set_sma_parameters(target_perc)

                    # Store percentage
                    last_state = target_perc

                    # Send mail
                    if SENDMAIL_FLAG:
                        html, status = self.create_html_status(target_perc, reason)
                        send_html_email(to=self.to_mail, api_key=self.resend_api_key, subject="Zonnebrand Status Update", html=html)
                else:
                    logger.info("No change needed (%d%%) | %s", target_perc, reason)

                # Append to CSV
                append_log_data(self.logfiles['status'], target_perc, reason)
                # Mark this iteration
                logger.info("--------------------------------------------")

            except requests.RequestException as exc:
                logger.error("Price API error: %s", exc)
            except Exception as exc:
                logger.error("Unexpected error: %s", exc, exc_info=True)
    
            # Sleep zzz...
            logger.info("Having a nap for %.0d minutes..", self.CHECK_INTERVAL_SECONDS / 60)
            time.sleep(self.CHECK_INTERVAL_SECONDS)
            
    # =============================================================================
    # PRICE FETCHING
    # =============================================================================
    def fetch_epex(self, date=None) -> dict:
        """Return the raw data as a dict.
        
        date: '2026-05-09'
        
        """
        
        if date is None:
            date = get_date_time('today')

        logger.info("Fetching new daily price data (%s)", date)
        self.data = None

        if self.COUNTRY == 'NL':
            data = self.fetch_dutch_energy_prices(date=date)
            self.data = data
            return data
        elif self.COUNTRY == 'DE':
            url = "https://api.awattar.de/v1/marketdata"
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            self.data = resp.json()
            return resp.json()
        else:
            raise ValueError(f"Unsupported country: {self.COUNTRY!r}. Supported: 'NL', 'DE'.")


    def fetch_dutch_energy_prices(self, date=None) -> list[dict]:
        """
        Get all 15-minute electricity price data from stroomperuur.nl.
        Returns a list of dicts with timestamp and €/MWh price.
        """
        if date is None:
            date = get_date_time('today')

        if self.provider == 'example':
            data = self.example_data()
        elif self.provider == 'api':
            data = _fetch_dutch_energy_prices_api(self.URL_STROOMPERUUR)
        else:
            # First try the fast direct JSON API (no browser needed).
            # Fall back to Playwright scraping only if the API call fails.
            try:
                data = fetch_stroomperuur(provider=self.provider, date=date)
            except Exception as e:
                logger.warning(
                    "fetch_stroomperuur API failed (%s). Falling back to Playwright.",
                    repr(e),
                )
                try:
                    data = asyncio.run(
                        _fetch_dutch_energy_prices_playwright(
                            self.URL_STROOMPERUUR,
                            provider=self.provider,
                            browser=self.browser,
                        )
                    )
                except Exception as e2:
                    logger.warning(
                        "Playwright fetch failed (%s). Falling back to generic API.",
                        repr(e2),
                    )
                    data = _fetch_dutch_energy_prices_api(self.URL_STROOMPERUUR)

        # Store provider in dict
        data = [{"provider": self.provider, **r} for r in data]
        # Return data
        return data

    def decide_target(self, data: list[dict]) -> tuple[int, str]:
        """Return (target_percent, reason). target_percent is 0 or 100."""

        # Get the now time
        now = datetime.now()

        # Convert "HH:MM" → datetime today
        parsed = []
        for s in data:
            t = datetime.strptime(s["time"], "%H:%M").replace(year=now.year, month=now.month, day=now.day)
            parsed.append((t, s["price"]))

        # Derive slot duration from actual data (15 min for 96 slots, 60 min for 24 slots)
        slot_minutes = 1440 // len(parsed) if len(parsed) in (24, 96) else 15
        slot_duration = timedelta(minutes=slot_minutes)

        # Find current slot by looping over all slots and filter only the one where <now> falls inside the slot interval:
        current = next((p for p in parsed if p[0] <= now < p[0] + slot_duration), None)

        if current:
            slot_start = current[0]
            slot_end = slot_start + slot_duration
            current_price = current[1]
            logger.info("Current price %.4f €/kWh in time-slot: %s - %s", current_price, slot_start.strftime("%d-%m-%Y %H:%M"), slot_end.strftime("%H:%M"))
        else:
            current_price = None
            logger.warning("No matching price slot found for current time.")

        # Detect negative window
        negative_blocks = []
        start = None
    
        for t, price in parsed:
            if price < 0:
                if start is None:
                    start = t
            else:
                if start is not None:
                    negative_blocks.append((start, t))
                    start = None
    
        if start is not None:
            negative_blocks.append((start, parsed[-1][0] + slot_duration))
    
        # Pick active window (if any overlaps now)
        active_window = next(((s, e) for s, e in negative_blocks if s <= now < e), None)
    
        # No negative window → charge allowed
        if active_window is None:
            price_str = f"{current_price:.4f} €/kWh" if current_price is not None else "unknown"
            return 100, f"no negative prices (current {price_str})"
        else:
            win_start, win_end = active_window
            window_minutes = (win_end - win_start).total_seconds() / 60

            if current_price is None: current_price = 0

            if window_minutes < self.MIN_WINDOW_MINUTES:
                return 100, (
                    f"negative window {window_minutes:.0f} min < {self.MIN_WINDOW_MINUTES} min "
                    f"ignored (price {current_price:.4f} €/kWh)"
                )

            return 0, (
                f"negative window {win_start.strftime('%H:%M')}-{win_end.strftime('%H:%M')} "
                f"({window_minutes:.0f} min), price {current_price:.4f} €/kWh"
            )


    def set_sma_parameters(self, value: int) -> None:
        """
        Thread-safe wrapper around the async Playwright logic.
    
        Playwright's sync API crashes when an asyncio event loop is already
        running (e.g. Jupyter, Spyder, IPython).  This wrapper always runs the
        async coroutine in a *fresh* event loop on a dedicated background thread,
        so it works correctly in every environment.
        """
        assert 0 <= value <= 100, "value must be 0–100"
        if not self.username or not self.password:
            raise ValueError("Missing SUNNY_USERNAME / SUNNY_PASSWORD")
    
        exc_holder: list[BaseException] = []
    
        def _run() -> None:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(_set_sma_parameters_async(value, self.URL_MAIN, self.username, self.password, browser=self.browser, tempdir=self.logfiles['tempdir'], screenshot=self.screenshot))
            except Exception as exc:
                exc_holder.append(exc)
            finally:
                loop.close()

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        t.join()
    
        if exc_holder:
            raise exc_holder[0]

        # Return
        return


    def plot(self, retrieve_data=None):
        """ Plot EPEX data.

        Parameters
        ----------
        retrieve_data : str
            'current' : Get current data
            'load'    : Load from saved file

        Returns
        -------
        None.

        """
        logger.info("Fetching EPEX prices…")
        dateData = get_date_time('today')
    
        # 1) Retrieve data
        if retrieve_data is None and not hasattr(self, 'data'):
            logger.error('data is not retrieved from EPEX. First run: client.fetch_epex() <return>')
            return None
        elif retrieve_data is None and self.data is not None:
            raw = self.data
        elif os.path.isfile(self.logfiles['epex']):
            # Load data from file
            raw = load_epex_data(self.logfiles['epex'])
            dateData = raw[0]['date']
        else:
            if retrieve_data == 'file':
                logger.error(f'{self.logfiles["epex"]} is not found <return>')
            else:
                logger.error('data is not retrieved from EPEX. First run: client.fetch_epex() <return>')
            return
    
    
            
        # 2) Extract vectors
        times  = [r["time"] for r in raw]
        prices = [r["price"] for r in raw]
        inkoop = None
        belasting = None
        # Update when data is available
        if raw[0].get('inkoop'):
            inkoop      = [r["inkoop"] for r in raw]
        if raw[0].get('belasting'):
            belasting   = [r["belasting"] for r in raw]
        
        # 3) Stats
        neg_count = sum(1 for p in prices if p < 0)
        avg = sum(prices) / len(prices)
        peak = max(prices)
        
        logger.info(
            "data: %d | Negative: %d | Avg: %.3f | Peak: %.3f",
            len(prices), neg_count, avg, peak
        )
        
        # 4) Plot
        fig = go.Figure()
        
        # Inkoop
        if inkoop is not None:
            fig.add_trace(go.Bar(
                x=times,
                y=inkoop,
                name="Inkoop",
                marker_color="#3498DB",
                hovertemplate="Time: %{x}<br>Inkoop: €%{y:.3f}<extra></extra>"
            ))
        
        # Belasting
        if belasting is not None:
            fig.add_trace(go.Bar(
                x=times,
                y=belasting,
                name="Belasting",
                marker_color="#F1C40F",
                hovertemplate="Time: %{x}<br>Belasting: €%{y:.3f}<extra></extra>"
            ))
        
        # Optional: total price line on top
        fig.add_trace(go.Scatter(
            x=times,
            y=prices,
            mode='lines+markers',
            name='Total price',
            line=dict(color='black', width=2),
            hovertemplate="Time: %{x}<br>Total: €%{y:.3f}<extra></extra>"
        ))
        
        fig.update_layout(
            title=(
                f"EPEX prices {self.provider} - {dateData}"
                f"<br>avg €{avg:.3f} | peak €{peak:.3f} "
                f"| negative {neg_count}"
            ),
            xaxis_title="Time",
            yaxis_title="€/kWh",
            template="plotly_white",
            height=500,
            barmode='stack',
            hovermode='x unified'
        )
        
        # Dynamic y-axis
        ymin = min(prices + [0])
        ymax = max(prices)
        padding = (ymax - ymin) * 0.1
        
        fig.update_yaxes(range=[ymin - padding, ymax + padding])
        
        fig.add_hline(y=0, line_width=2, line_color="black")
        
        # 6) Open in browser
        tmp = os.path.join(self.logfiles['tempdir'], f'{self.provider}_epex_prices.html')        
        fig.write_html(tmp, auto_open=True)


    def example_data(self):
        data = [{'time': '0:00', 'price': 0.26377}, {'time': '0:15', 'price': 0.25477}, {'time': '0:30', 'price': 0.25566}, {'time': '0:45', 'price': 0.25061}, {'time': '1:00', 'price': 0.25396}, {'time': '1:15', 'price': 0.25351}, {'time': '1:30', 'price': 0.25115}, {'time': '1:45', 'price': 0.24641}, {'time': '2:00', 'price': 0.24579}, {'time': '2:15', 'price': 0.24733}, {'time': '2:30', 'price': 0.25245}, {'time': '2:45', 'price': 0.24986}, {'time': '3:00', 'price': 0.24614}, {'time': '3:15', 'price': 0.24458}, {'time': '3:30', 'price': 0.2427}, {'time': '3:45', 'price': 0.24603}, {'time': '4:00', 'price': 0.24016}, {'time': '4:15', 'price': 0.23885}, {'time': '4:30', 'price': 0.23927}, {'time': '4:45', 'price': 0.24002}, {'time': '5:00', 'price': 0.23771}, {'time': '5:15', 'price': 0.24067}, {'time': '5:30', 'price': 0.24044}, {'time': '5:45', 'price': 0.24309}, {'time': '6:00', 'price': 0.24144}, {'time': '6:15', 'price': 0.23675}, {'time': '6:30', 'price': 0.23787}, {'time': '6:45', 'price': 0.22687}, {'time': '7:00', 'price': 0.25977}, {'time': '7:15', 'price': 0.23098}, {'time': '7:30', 'price': 0.20966}, {'time': '7:45', 'price': 0.20563}, {'time': '8:00', 'price': 0.22351}, {'time': '8:15', 'price': 0.21297}, {'time': '8:30', 'price': 0.20369}, {'time': '8:45', 'price': 0.19391}, {'time': '9:00', 'price': 0.21676}, {'time': '9:15', 'price': 0.16768}, {'time': '9:30', 'price': 0.15371}, {'time': '9:45', 'price': 0.13496}, {'time': '10:00', 'price': 0.15325}, {'time': '10:15', 'price': 0.14587}, {'time': '10:30', 'price': 0.13574}, {'time': '10:45', 'price': 0.12953}, {'time': '11:00', 'price': 0.14453}, {'time': '11:15', 'price': 0.13903}, {'time': '11:30', 'price': 0.13874}, {'time': '11:45', 'price': 0.13823}, {'time': '12:00', 'price': 0.13833}, {'time': '12:15', 'price': 0.14435}, {'time': '12:30', 'price': 0.1473}, {'time': '12:45', 'price': 0.15167}, {'time': '13:00', 'price': -0.14458}, {'time': '13:15', 'price': -0.15183}, {'time': '13:30', 'price': -0.15371}, {'time': '13:45', 'price': -0.15377}, {'time': '14:00', 'price': -0.16231}, {'time': '14:15', 'price': -0.16722}, {'time': '14:30', 'price': -0.15375}, {'time': '14:45', 'price': -0.15371}, {'time': '15:00', 'price': 0.15361}, {'time': '15:15', 'price': 0.15603}, {'time': '15:30', 'price': 0.16871}, {'time': '15:45', 'price': 0.18298}, {'time': '16:00', 'price': 0.17555}, {'time': '16:15', 'price': 0.18569}, {'time': '16:30', 'price': 0.19179}, {'time': '16:45', 'price': 0.20618}, {'time': '17:00', 'price': 0.14626}, {'time': '17:15', 'price': 0.2241}, {'time': '17:30', 'price': 0.27526}, {'time': '17:45', 'price': 0.30899}, {'time': '18:00', 'price': 0.23384}, {'time': '18:15', 'price': 0.24999}, {'time': '18:30', 'price': 0.261}, {'time': '18:45', 'price': 0.2686}, {'time': '19:00', 'price': 0.26904}, {'time': '19:15', 'price': 0.26569}, {'time': '19:30', 'price': 0.281}, {'time': '19:45', 'price': 0.30019}, {'time': '20:00', 'price': 0.28287}, {'time': '20:15', 'price': 0.2855}, {'time': '20:30', 'price': 0.2874}, {'time': '20:45', 'price': 0.29011}, {'time': '21:00', 'price': 0.28516}, {'time': '21:15', 'price': 0.27868}, {'time': '21:30', 'price': 0.27294}, {'time': '21:45', 'price': 0.26659}, {'time': '22:00', 'price': 0.27702}, {'time': '22:15', 'price': 0.27755}, {'time': '22:30', 'price': 0.26197}, {'time': '22:45', 'price': 0.25462}, {'time': '23:00', 'price': 0.27039}, {'time': '23:15', 'price': 0.25566}, {'time': '23:30', 'price': 0.2494}, {'time': '23:45', 'price': 0.24597}]
        # Store date in dict
        data = [{"date": get_date_time('today'), **r} for r in data]
        # Store provider in dict
        data = [{"provider": self.provider, **r} for r in data]
        # return
        return data


    def create_html_status(self, target_perc: int, reason: str):
        """
        Send automated status update mail.
    
        Parameters
        ----------
        target_perc : int
            Target percentage (0 or 100)
        reason : str
            Decision reason returned by decide_target()
        """
    
        status = "SOLAR PANELS ACTIVE" if target_perc == 100 else "SOLAR PANELS DISABLED"
    
        color = "#16a34a" if target_perc == 100 else "#dc2626"
    
        now_str = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; background:#f5f5f5; padding:20px;">
    
            <div style="
                max-width:700px;
                margin:auto;
                background:white;
                border-radius:12px;
                padding:24px;
                box-shadow:0 2px 10px rgba(0,0,0,0.08);
            ">
    
                <h2 style="margin-top:0; color:{color};">
                    Solar Panels Status:
                </h2>
    
                <div style="
                    background:{color};
                    color:white;
                    padding:14px;
                    border-radius:8px;
                    font-size:20px;
                    font-weight:bold;
                    text-align:center;
                    margin-bottom:20px;
                ">
                    {status}
                </div>
    
                <table style="width:100%; border-collapse:collapse; font-size:15px;">
    
                    <tr>
                        <td style="padding:10px; border-bottom:1px solid #ddd;">
                            <b>Target Percentage</b>
                        </td>
    
                        <td style="padding:10px; border-bottom:1px solid #ddd;">
                            {target_perc}%
                        </td>
                    </tr>
    
                    <tr>
                        <td style="padding:10px; border-bottom:1px solid #ddd;">
                            <b>Decision Reason</b>
                        </td>
    
                        <td style="padding:10px; border-bottom:1px solid #ddd;">
                            {reason}
                        </td>
                    </tr>
    
                    <tr>
                        <td style="padding:10px; border-bottom:1px solid #ddd;">
                            <b>Timestamp</b>
                        </td>
    
                        <td style="padding:10px; border-bottom:1px solid #ddd;">
                            {now_str}
                        </td>
                    </tr>
    
                </table>
    
                <p style="margin-top:24px; color:#666; font-size:13px;">
                    Automated Zonnebrand management notification.
                </p>
    
            </div>
    
        </body>
        </html>
        """
        
        return html, status
    

# %%
def get_date_time(format_type = 'today', UTC=True):
    now = datetime.now(timezone.utc) if UTC else datetime.now()

    if format_type=='today':
        return date.today().isoformat()
    elif format_type=='time':
        return now.strftime("%H:%M")
    elif format_type=='object':
        return now
    elif format_type=='%H%M%S':
        return now.strftime("%H%M%S")
    elif format_type=='today_object':
        return now.date()


def load_epex_data(datafile):
    if not os.path.exists(datafile):
        raise FileNotFoundError(f"Data file not found: {datafile}")

    rows = []
    with open(datafile, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({
                "date": row["date"],
                "time": row["time"],
                "price": float(row["price"])
            })

    logger.info(f"Loaded {len(rows)} rows from {datafile}")

    # Deduplicate by full datetime
    # Key: "YYYY-MM-DD HH:MM"
    unique = {}
    for r in rows:
        key = f"{r['date']} {r['time']}"
        unique[key] = r   # last one wins (append-safe)

    # Sort by datetime
    def parse_dt(r):
        return datetime.strptime(f"{r['date']} {r['time']}", "%Y-%m-%d %H:%M")

    sorted_rows = sorted(unique.values(), key=parse_dt)

    logger.info(f"Returning {len(sorted_rows)} unique sorted rows")
    return sorted_rows

            
# =============================================================================
# EXTRACT 15-MINUTE ENERGY PRICES
# =============================================================================
def _fetch_dutch_energy_prices_api(url):
    # Always request 15-minute interval data (?kwartier=1).
    # Add the parameter if it isn't already present in the URL.
    if "kwartier=1" not in url:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}kwartier=1"

    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    html = resp.text

    # usage
    data = parse_prices(html)
    # Add current date
    today = get_date_time('today')
    # Store in dict
    data = [{"date": today, **r} for r in data]
    # Show in logger
    # logger.info(json.dumps(data[:2], indent=2))
    # return
    return data


def parse_prices(html):
    # labels
    labels = re.search(r"labels:\s*\[(.*?)\]", html, re.DOTALL).group(1)
    labels = [x.strip().strip('"') for x in labels.split(',') if x.strip()]

    pattern = r"label:\s*'([^']+)'.*?data:\s*\[(.*?)\]"
    matches = re.findall(pattern, html, re.DOTALL)
    data_map = {label: vals for label, vals in matches}
    inkoop = [float(x) for x in data_map['Inkoopprijs per kWh'].split(',') if x.strip()]
    belasting = [float(x) for x in data_map['Energiebelasting en BTW'].split(',') if x.strip()]
    
    result = []
    for t, i, b in zip(labels, inkoop, belasting):
        result.append({"time": t, "price": round(i + b, 5)})

    # Return
    return result


def get_provider_option(name: str) -> str:
    PROVIDERS = {
        "all_in_power": "4",
        "anwb": "3",
        "budget": "15",
        "coolblue": "10",
        "delta": "22",
        "easyenergy": "5",
        "eneco": "17",
        "vanons": "6",
        "energiedirect": "16",
        "energiek": "21",
        "energyzero": "7",
        "engie": "23",
        "essent": "20",
        "frank": "8",
        "groenelokaal": "9",
        "nextenergy": "11",
        "oxxio": "19",
        "powerpeers": "24",
        "tibber": "1",
        "vandebron": "14",
        "vattenfall": "18",
        "vrijopnaam": "12",
        "zonneplan": "2",
    }

    key = name.lower().replace(" ", "").replace("_", "")
    if key not in PROVIDERS:
        logger.warning(f"Unknown provider: {name}. Set to api.")
        return 'api'
    else:
        logger.info(f"provider set to: {name}")
        return PROVIDERS[key]


def fetch_stroomperuur(provider: str = 'api', date: str = None) -> list[dict]:
    """Fetch 15-minute electricity price data directly from the stroomperuur.nl JSON API.

    This calls ``/ajax/tarieven.php`` — the same endpoint the website's own
    chart uses — so no browser automation is needed.

    Parameters
    ----------
    provider : str
        Energy provider name (e.g. ``'zonneplan'``, ``'anwb'``, ``'tibber'``).
        Use ``'api'`` to get the generic EPEX spot price without a provider markup.
    date : str, optional
        Date in ``YYYY-MM-DD`` format.  Defaults to today.

    Returns
    -------
    list[dict]
        Each entry has ``date``, ``time`` (``HH:MM``), and ``price`` (€/kWh,
        inkoop + energiebelasting en BTW).

    Notes
    -----
    Response layout (list index → meaning):
      * ``data[0]``  – inkoopprijs per kWh per 15-min slot  (list of floats)
      * ``data[1]``  – energiebelasting en BTW per slot       (list of floats)
      * ``data[2]``  – gemiddelde totaalprijs                 (single float)
      * ``data[3]``  – vaste inkoopvergoeding                 (single float)

    Examples
    --------
    >>> rows = fetch_stroomperuur('zonneplan')
    >>> rows[0]
    {'date': '2025-05-09', 'time': '0:00', 'price': 0.27345}
    """
    BASE_URL = "https://stroomperuur.nl/ajax/tarieven.php"

    if date is None:
        date = get_date_time('today')

    provider_id = get_provider_option(provider)

    # 'api' means no specific provider → omit the leverancier parameter so the
    # site returns the raw EPEX spot price (same as the default page view).
    # kwartier=1 requests 15-minute slots (96/day) instead of hourly (24/day).
    params: dict = {"datum": date, "kwartier": "1"}
    if provider_id != 'api':
        params["leverancier"] = provider_id

    logger.info("fetch_stroomperuur: GET %s params=%s", BASE_URL, params)

    resp = requests.get(BASE_URL, params=params, timeout=15)
    resp.raise_for_status()

    payload = resp.json()
    # payload is a list: [inkoop_list, belasting_list, gem_prijs, inkoopvergoeding]
    inkoop    = payload[0]   # €/kWh – raw spot per 15-min slot
    belasting = payload[1]   # €/kWh – taxes+VAT per slot

    if len(inkoop) != len(belasting):
        raise ValueError(
            f"fetch_stroomperuur: mismatched slot counts "
            f"(inkoop={len(inkoop)}, belasting={len(belasting)})"
        )

    n = len(inkoop)
    if n not in (24, 96):
        logger.warning("fetch_stroomperuur: unexpected slot count %d (expected 96)", n)
    elif n == 24:
        logger.warning(
            "fetch_stroomperuur: received 24 hourly slots despite kwartier=1 – "
            "the API may not support 15-min for this provider/date combination."
        )

    # Derive interval from actual slot count so labels are always correct.
    interval_minutes = 1440 // n   # 1440 min/day / slots  ->  15 or 60

    # Build time labels HH:MM (e.g. 00:00, 00:15, 23:45)
    result = []
    for i, (ink, bel) in enumerate(zip(inkoop, belasting)):
        total_minutes = i * interval_minutes
        hour   = total_minutes // 60
        minute = total_minutes % 60
        time_label = f"{hour:02d}:{minute:02d}"
        result.append({
            "date":     date,
            "time":     time_label,
            "price":    round(ink + bel, 5),
            "inkoop":   ink,
            "belasting": bel,
        })

    logger.info(
        "fetch_stroomperuur: %d slots fetched for %s (provider=%s)",
        len(result), date, provider,
    )
    return result


async def _fetch_dutch_energy_prices_playwright(url, provider: str = 'api', browser: bool = False) -> list[dict]:
    # Get provider
    provider_option = get_provider_option(provider)
    
    # If no provider is found, then return the default one
    if provider_option=='api':
        data = _fetch_dutch_energy_prices_api(url)
        return data

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=browser)
        page = await browser.new_page()

        await page.goto(url, wait_until="networkidle")

        # 1 Ensure 15-min interval is ON
        checkbox = page.locator("#frm_uurofkwartier")
        if not await checkbox.is_checked():
            await checkbox.click()

        # 2. Select Zonneplan (value = "2")
        await page.select_option("#frm_leverancier", value=provider_option)

        await page.reload()

        # 3. Wait until chart updates (no hard sleep)
        await page.wait_for_function("""
        () => {
            const chart = Chart.getChart("chartStroom");
            if (!chart) return false;
        
            const labels = chart.data.labels;
            return labels.length > 0 && labels[labels.length - 1] === "23:45";
        }
        """)
        
        # Wait for chart to update
        await page.wait_for_timeout(1500)

        # Extract Chart.js data directly from the page
        data = await page.evaluate("""
        () => {
            const chart = Chart.getChart("chartStroom");
            if (!chart) return [];

            const labels = chart.data.labels;
            const datasets = chart.data.datasets;

            // Sum stacked bars: inkoop + vergoeding + belasting
            const prices = labels.map((_, i) => {
                let total = 0;
                datasets.forEach(ds => {
                    if (Array.isArray(ds.data) && typeof ds.data[i] === "number") {
                        total += ds.data[i];
                    }
                });
                return total;
            });

            return labels.map((t, i) => ({
                time: t,
                price: prices[i]
            }));
        }
        """)

        await browser.close()
        # await page.wait_for_timeout(15000)
        return data

# %%
def append_epex_prices(filepath, data):
    """
    Append 15‑minute price data to CSV.
    Creates directory + file + header if missing.
    Each row: YYYY‑MM‑DD, HH:MM, price
    """
    filepath = os.path.expanduser(filepath)
    directory = os.path.dirname(filepath)

    # Ensure directory exists
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)

    # Check file exists
    file_exists = os.path.exists(filepath)

    # Open in append mode
    with open(filepath, "a", newline="", encoding="utf-8") as f:
        # Init writer
        writer = csv.writer(f)
        # Write header only once
        if not file_exists: writer.writerow(["date", "time", "price", "provider"])
        # Get today
        today = get_date_time('today')
        # Append to file
        for entry in data: writer.writerow([today, entry["time"], entry["price"], entry["provider"]])


def append_log_data(filepath, target_perc=None, reason=None):
    if not os.path.exists(filepath):
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["date", "time", "target_percent", "reason"])
        logger.info(f"Created new logfile with header: {filepath}")

    # Create new line if percentage aka target_perc is known
    if target_perc and filepath and os.path.isfile(filepath):
        logger.info(f"Logfile is appended: {filepath}")

        # Get today
        today = get_date_time('today')
        time = get_date_time('time')
        # Write
        with open(filepath, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([today, time, target_perc, reason])

# =============================================================================
# CONTROL LOGIC
# =============================================================================
def get_current_negative_window(slots: list[dict]) -> tuple[datetime | None, datetime | None]:
    """
    Find the contiguous block of negative-price slots that covers *now*.
    Returns (window_start, window_end) or (None, None).
    """
    now = get_date_time(format_type='object')

    current_idx = None
    for i, slot in enumerate(slots):
        if slot["start"] <= now < slot["end"]:
            current_idx = i
            break

    if current_idx is None or slots[current_idx]["price_eur_kwh"] >= 0:
        return None, None

    start_idx = current_idx
    while start_idx > 0 and slots[start_idx - 1]["price_eur_kwh"] < 0:
        start_idx -= 1

    end_idx = current_idx
    while end_idx < len(slots) - 1 and slots[end_idx + 1]["price_eur_kwh"] < 0:
        end_idx += 1

    return slots[start_idx]["start"], slots[end_idx]["end"]


# =============================================================================
# SUNNY PORTAL – SET BOTH PARAMETERS
# =============================================================================
async def _screenshot(page, label, tempdir=None) -> None:
    """Save a debug screenshot and log its path."""
    ts = get_date_time(format_type="%H%M%S")
    
    safe = label.replace(" ", "_").replace("/", "-")
    if tempdir is None:
        tempdir = tempfile.gettempdir()
    path = os.path.join(tempdir, f"sma_{ts}_{safe}.png")
    await page.screenshot(path=path, full_page=True)
    logger.info("      \U0001f4f8 screenshot \u2192 %s", path)


async def _set_param_via_search(page, key: str, value: int, tempdir=None, screenshot=False) -> bool:
    logger.info("      Searching for parameter %r …", key)

    # Search box at top: "Groep, naam of kanaal invoeren..."
    search_box = page.locator('input.mat-mdc-input-element[placeholder="Groep, naam of kanaal invoeren..."]').first

    await search_box.wait_for(state="visible", timeout=10_000)
    await search_box.click()
    # clear previous search
    await search_box.fill("")
    await search_box.fill(key)
    await search_box.press("Enter")
    # let Angular update results
    await page.wait_for_timeout(800)

    # Now there should be exactly one row with one editable parameter input
    # Important: exclude the search box itself (mat-input-0)
    param_input = page.locator('input.mat-mdc-input-element:not(#mat-input-0)').first

    try:
        await param_input.wait_for(state="visible", timeout=10_000)
    except PWTimeout:
        logger.warning("No parameter input visible for key %r", key)
        if screenshot:
            await _screenshot(page, f"missing_param_{key}", tempdir)
        return False

    current_val = await param_input.input_value()
    logger.info("       >[%s] current value: %r | target: %s", key, current_val, value)

    if str(current_val).strip() == str(value):
        logger.info("       >[%s] → already correct, skipping", key)
        return False

    await param_input.scroll_into_view_if_needed()    
    # Option A: triple-click via click_count
    await param_input.click(click_count=3, delay=50)
    # Option B (even safer): select-all via Ctrl+A
    # await param_input.click()
    # await param_input.press("Control+A")    
    await param_input.fill(str(value))
    await param_input.press("Tab")
    await page.wait_for_timeout(600)

    logger.info("  [%s] → filled with %d", key, value)
    if screenshot:
        await _screenshot(page, f"filled_{key}", tempdir)

    # Optional: click Save/OK if it appears
    save_btn = page.locator(
        "button:has-text('Opslaan'), button:has-text('Save'), "
        "button:has-text('Bevestigen'), button:has-text('OK')"
    ).first
    try:
        await save_btn.wait_for(state="visible", timeout=2_000)
        logger.info("  [%s] Save button found, clicking …", key)
        await save_btn.click()
        await page.wait_for_timeout(800)
        if screenshot: 
            await _screenshot(page, f"saved_{key}", tempdir)
    except PWTimeout:
        logger.info("  [%s] No save button appeared (auto-save or not needed)", key)

    return True



# =============================================================================
# SMA
# =============================================================================
async def _set_sma_parameters_async(value, SUNNY_URL, USERNAME, PASSWORD, browser=False, tempdir=None, screenshot=False) -> None:
    """Async Playwright implementation – visible browser with full debug output."""

    async with async_playwright() as p:
        # browser=False so you can watch every step in the real browser window
        browser = await p.chromium.launch(headless=browser, slow_mo=150)
        context = await browser.new_context(viewport={"width": 1280, "height": 900})
        page    = await context.new_page()

        # ── Forward browser console to Python logger ─────────────────────────
        page.on("console", lambda msg: logger.debug("  [browser %s] %s", msg.type, msg.text))
        page.on("pageerror", lambda exc: logger.error("  [browser error] %s", exc))
        page.on("request",  lambda req: logger.debug("  >> %s %s", req.method, req.url[:120]))
        page.on("response", lambda res: logger.debug("  << %s %s", res.status, res.url[:120]))

        try:
            # =============================================================================
            # ── Step 1: Landing page ───────────────────────────────────────
            # =============================================================================
            logger.info("[1/6] Opening ennexOS landing page \u2026")
            await page.goto("https://ennexos.sunnyportal.com", timeout=30_000)
            await page.wait_for_load_state("networkidle")
            logger.info("      URL: %s | title: %s", page.url, await page.title())
            if screenshot:
                await _screenshot(page, "1_landing_page", tempdir)

            # =============================================================================
            # ── Step 2: Click Login button to open the credentials form ──────
            # =============================================================================
            logger.info("[2/6] Clicking Login button to open credentials form \u2026")
            login_btn = page.locator('button[data-testid="button-primary"]')
            await login_btn.wait_for(state="visible", timeout=10_000)
            logger.info("      Button text: %r", await login_btn.inner_text())
            await login_btn.click()
            await page.wait_for_load_state("networkidle")
            logger.debug("      URL after click: %s | title: %s", page.url, await page.title())
            if screenshot:
                await _screenshot(page, "2_credentials_form", tempdir)

            # =============================================================================
            # ── Step 3: Fill credentials and submit ─────────────────────
            # =============================================================================
            logger.info("[3/6] Waiting for credentials form \u2026")
            await page.wait_for_selector('#username', timeout=15_000)
            logger.info("      Filling username and password \u2026")
            await page.fill('#username', USERNAME)
            await page.fill('#password', PASSWORD)
            if screenshot:
                await _screenshot(page, "3_credentials_filled", tempdir)

            logger.info("      Submitting credentials \u2026")
            await page.click('button.btn-primary[name="login"]')
            await page.wait_for_load_state("networkidle")
            logger.debug("      Post-login URL: %s | title: %s", page.url, await page.title())
            if screenshot:
                await _screenshot(page, "4_after_login", tempdir)

            # =============================================================================
            # Detect common failure modes
            # =============================================================================
            if "login" in page.url.lower() or "error" in page.url.lower():
                logger.error("Login may have failed – still on login/error page!")
            if await page.locator("text=incorrect").count():
                logger.error("Page contains 'incorrect' – wrong credentials?")

            # =============================================================================
            # ── Navigate to parameters page ──────────────────────────────────
            # =============================================================================
            logger.info("[4/6] Navigating to parameters page \u2026")
            await page.goto(SUNNY_URL, timeout=30_000)
            await page.wait_for_load_state("networkidle")
            logger.info("      URL: %s | title: %s", page.url, await page.title())
            if screenshot:
                await _screenshot(page, "4_parameters_page", tempdir)

            # =============================================================================
            # Wait for Angular to render inputs
            # =============================================================================
            logger.info("      Waiting for Angular inputs to render \u2026")
            await page.wait_for_selector('input.mat-mdc-input-element', timeout=20_000)
            all_inputs = await page.locator('input.mat-mdc-input-element').all()
            logger.info("      Found %d mat-input element(s) on page", len(all_inputs))
            for i, inp in enumerate(all_inputs):
                aria = await inp.get_attribute("aria-labelledby") or ""
                val  = await inp.input_value()
                logger.info("       >input[%d] aria-labelledby=%r  value=%r", i, aria, val)

            # =============================================================================
            # ── Set each target parameter ────────────────────────────────────
            # =============================================================================
            logger.info("[5/6] Updating parameters to %d%% \u2026", value)
            changed = 0
            
            for key in ["Parameter.PCC.FlbInv.WMaxNom", "Parameter.PCC.WMaxNom"]:
                updated = await _set_param_via_search(page, key, value, tempdir=tempdir, screenshot=screenshot)
                if updated:
                    changed += 1
            
            logger.info("[6/6] Done – %d parameter(s) updated to %d%%", changed, value)
            if screenshot:
                await _screenshot(page, "7_final_state", tempdir)
            
            if changed == 0:
                logger.warning("No parameters were changed – check parameter keys or UI layout.")
            
        except PWTimeout as exc:
            logger.error("Playwright timeout: %s", exc)
            if screenshot:
                await _screenshot(page, "ERROR_timeout", tempdir)
            raise
        except Exception as exc:
            logger.error("Unexpected error: %s", exc)
            if screenshot:
                await _screenshot(page, "ERROR_unexpected", tempdir)
            raise
        finally:
            logger.info("Closing browser \u2026")
            await page.wait_for_timeout(1_000)   # brief pause so you can see final state
            await browser.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Zonnebrand SMA controller"
    )

    parser.add_argument(
        "--plot",
        action="store_true",
        help="Fetch prices and open the interactive chart in the browser.",
    )

    parser.add_argument(
        "--browser",
        action="store_false",
        help="Show the browser when active.",
    )

    parser.add_argument(
        "--data",
        action="store_true",
        help="Fetch prices and print them and return",
    )

    parser.add_argument(
        "--provider",
        type=str,
        default='api',
        help="Energy provider (e.g. zonneplan, tibber, essent)",
    )

    parser.add_argument(
        "--mail",
        type=str,
        default=None,
        help="Mail address to send the status updates",
    )

    parser.add_argument(
        "--set",
        type=int,
        choices=range(0, 101),
        metavar="{0..100}",
        default=None,
        help=(
            "Set the export-limit percentage (0–100) and exit immediately, "
            "bypassing all price-based logic."
        ),
    )

    # Parse all arguments
    args = parser.parse_args()
    # Get provider
    provider = args.provider.lower()

    check_keys = load_dotenv("../.secrets/keys")
    if not check_keys:
        load_dotenv(".secrets/keys")
    
    # get keys
    USERNAME = os.getenv("SUNNY_USERNAME")
    PASSWORD = os.getenv("SUNNY_PASSWORD")
    RESEND_API_KEY = os.getenv("RESEND_API_KEY")

    # Load library
    from zonnebrand import Zonnebrand
    # Initialize
    client = Zonnebrand(username=USERNAME,
                        password=PASSWORD,
                        provider=provider,
                        # showplot=args.plot,
                        browser=args.browser,
                        resend_api_key=RESEND_API_KEY,
                        to_mail=args.mail,
                        )

    if args.data:
        data = client.fetch_epex()
        # data = asyncio.run(_fetch_dutch_energy_prices_playwright(client.URL_STROOMPERUUR, provider=provider, browser=args.browser))
        print(data)
    elif args.set is not None:
        if not USERNAME or not PASSWORD: raise ValueError("Missing SUNNY_USERNAME / SUNNY_PASSWORD in .secrets")
        logger.info("Manual override: setting export limit to %d%%", args.set)
        # Set directly the percentage in SMA
        client.set_sma_parameters(args.set)
        logger.info("Done.")
    else:
        if not USERNAME or not PASSWORD: raise ValueError("Missing SUNNY_USERNAME / SUNNY_PASSWORD in .secrets")
        # Run main
        client.run()