"""
Zonnebrand — Flask server + process manager
============================================
Designed to run headlessly on a Raspberry Pi (no display).
Imports Zonnebrand directly and runs it in a daemon thread —
no subprocess, no PATH guessing, no display required.

Start:
    python server.py

Then open http://<pi-ip>:8000/setup  from any browser on your network.
"""

from flask import Flask, send_from_directory, jsonify, request
import csv
import os
import sys
import json
import threading
import logging
from collections import deque
from datetime import datetime, date

app = Flask(__name__)
log = logging.getLogger(__name__)

DATA_DIR    = './dashboard'
EPEX_CSV    = os.path.join(DATA_DIR, 'epex.csv')
SOLAR_CSV   = os.path.join(DATA_DIR, 'zonnebrand.csv')
CONFIG_FILE = os.path.join(DATA_DIR, 'config.json')

os.makedirs(DATA_DIR, exist_ok=True)


# ══════════════════════════════════════════════════════════════════════════════
# IN-PROCESS LOG HANDLER
# Captures all Python logging output into a ring buffer so the dashboard
# can stream it without needing stdout of a subprocess.
# ══════════════════════════════════════════════════════════════════════════════

class RingBufferHandler(logging.Handler):
    """Logging handler that keeps the last N log records in memory."""

    def __init__(self, maxlen=500):
        super().__init__()
        self._buf  = deque(maxlen=maxlen)
        self._lock = threading.Lock()

    def emit(self, record):
        line = self.format(record)
        ts   = datetime.now().strftime('%H:%M:%S')
        with self._lock:
            self._buf.append(f'[{ts}] {line}')

    def tail(self, n=100):
        with self._lock:
            lines = list(self._buf)
        return lines[-n:]

    def clear(self):
        with self._lock:
            self._buf.clear()


# Install ring-buffer handler on root logger so all zonnebrand log calls
# are captured automatically.
_ring = RingBufferHandler(maxlen=500)
_ring.setFormatter(logging.Formatter('%(levelname)-7s  %(name)s  %(message)s'))
logging.getLogger().addHandler(_ring)
logging.getLogger().setLevel(logging.INFO)


# ══════════════════════════════════════════════════════════════════════════════
# CONTROLLER THREAD MANAGER
# ══════════════════════════════════════════════════════════════════════════════

class ControllerManager:
    """
    Runs Zonnebrand.run() in a daemon thread.
    Thread-safe start / stop / status / logs.
    """

    def __init__(self):
        self._thread     = None
        self._stop_event = threading.Event()
        self._lock       = threading.Lock()
        self._start_time = None
        self._error      = None
        self._client     = None   # live Zonnebrand instance (for manual-set)

    # ── public ───────────────────────────────────────────────────────────────

    def start(self, config: dict) -> dict:
        with self._lock:
            if self._thread and self._thread.is_alive():
                return {'ok': False, 'error': 'Controller is already running. Stop it first.'}

            self._stop_event.clear()
            self._error = None
            _ring.clear()

            try:
                client = self._build_client(config)
            except Exception as exc:
                return {'ok': False, 'error': str(exc)}

            self._client     = client
            self._start_time = datetime.now()

            self._thread = threading.Thread(
                target=self._run_loop,
                args=(client,),
                daemon=True,
                name='zonnebrand-controller',
            )
            self._thread.start()
            log.info('[server] Controller thread started.')
            return {'ok': True}

    def stop(self) -> dict:
        with self._lock:
            if not self._thread or not self._thread.is_alive():
                return {'ok': False, 'error': 'Controller is not running.'}
            self._stop_event.set()
            # Wake up the sleeping loop immediately
            if self._client:
                self._client._stop_event = self._stop_event
            log.info('[server] Stop signal sent to controller.')
            return {'ok': True}

    def status(self) -> dict:
        running  = self._thread is not None and self._thread.is_alive()
        uptime   = None
        if running and self._start_time:
            secs   = int((datetime.now() - self._start_time).total_seconds())
            h, rem = divmod(secs, 3600)
            m, s   = divmod(rem, 60)
            uptime = f'{h}h {m:02d}m {s:02d}s'
        return {
            'running':    running,
            'uptime':     uptime,
            'error':      self._error,
            'start_time': self._start_time.isoformat() if self._start_time else None,
        }

    def logs(self, n=100):
        return _ring.tail(n)

    def manual_set(self, config: dict, percent: int) -> dict:
        """Fire a one-shot set_sma_parameters call (blocking, max 2 min)."""
        try:
            client = self._build_client(config)
            client.set_sma_parameters(percent)
            return {'ok': True}
        except Exception as exc:
            return {'ok': False, 'error': str(exc)}

    # ── private ───────────────────────────────────────────────────────────────

    @staticmethod
    def _build_client(config: dict):
        """Import Zonnebrand and construct a configured instance."""
        # Make sure zonnebrand.py is importable from the current directory
        cwd = os.path.dirname(os.path.abspath(__file__))
        if cwd not in sys.path:
            sys.path.insert(0, cwd)

        try:
            from zonnebrand import Zonnebrand
        except ImportError as exc:
            raise RuntimeError(
                f'Cannot import Zonnebrand: {exc}. '
                'Make sure zonnebrand.py is in the same directory as server.py.'
            )

        username = config.get('username', '').strip()
        password = config.get('password', '').strip()
        if not username or not password:
            raise ValueError('SMA username and password are required.')

        client = Zonnebrand(
            username        = username,
            password        = password,
            provider        = config.get('provider', 'api'),
            showplot        = False,          # never show plot on Pi
            browser         = False,          # always headless on Pi
            resend_api_key  = config.get('resend_api_key') or None,
            to_mail         = config.get('mail') or None,
            screenshot      = config.get('screenshot', False),
            logdir          = config.get('logdir', DATA_DIR),
        )

        # Apply tunables that are only instance vars (not CLI args)
        if config.get('min_window_minutes'):
            client.MIN_WINDOW_MINUTES = int(config['min_window_minutes'])
        if config.get('check_interval_minutes'):
            client.CHECK_INTERVAL_SECONDS = int(config['check_interval_minutes']) * 60
        if config.get('country'):
            client.COUNTRY = config['country'].upper()

        return client

    def _run_loop(self, client):
        """
        Mirrors Zonnebrand.run() but checks _stop_event between iterations
        so the thread can be stopped cleanly from the web UI.
        """
        import time
        import requests

        log.info('[server] Entering control loop.')
        last_state  = None
        cached_data = None
        cache_date  = None

        try:
            from zonnebrand import (
                get_date_time, append_epex_prices, append_SMA_data,
            )
            try:
                from sendmail import send_html_email
                SENDMAIL_FLAG = True
            except Exception:
                SENDMAIL_FLAG = False
        except ImportError as exc:
            self._error = str(exc)
            log.error('[server] Import error in run loop: %s', exc)
            return

        while not self._stop_event.is_set():
            try:
                today = get_date_time(format_type='today_object')

                # Refresh price data once per calendar day
                if cached_data is None or cache_date != today:
                    cached_data = client.fetch_epex()
                    cache_date  = today
                    append_epex_prices(client.logfiles['epex'], cached_data)
                    log.debug('[server] Cached %d price slots.', len(cached_data))

                target_perc, reason = client.decide_target(cached_data)

                if target_perc != last_state:
                    log.info('[server] State change → %d%% | %s', target_perc, reason)
                    client.set_sma_parameters(target_perc)
                    last_state = target_perc
                    if SENDMAIL_FLAG and client.to_mail:
                        try:
                            html, _ = client.create_html_status(target_perc, reason)
                            send_html_email(
                                to      = client.to_mail,
                                api_key = client.resend_api_key,
                                subject = 'Zonnebrand Status Update',
                                html    = html,
                            )
                        except Exception as mail_exc:
                            log.warning('[server] Mail failed: %s', mail_exc)
                else:
                    log.info('[server] No change (%d%%) | %s', target_perc, reason)

                append_SMA_data(client.logfiles['sma'], target_perc, reason)
                log.info('[server] ────────────────────────────────')

            except requests.RequestException as exc:
                log.error('[server] Price API error: %s', exc)
            except Exception as exc:
                log.error('[server] Unexpected error: %s', exc, exc_info=True)
                self._error = str(exc)

            # Sleep in short increments so stop_event is checked regularly
            interval = client.CHECK_INTERVAL_SECONDS
            log.info('[server] Sleeping %d min until next check.', interval // 60)
            for _ in range(interval):
                if self._stop_event.is_set():
                    break
                import time as _t
                _t.sleep(1)

        log.info('[server] Controller loop exited cleanly.')


_ctrl = ControllerManager()


# ══════════════════════════════════════════════════════════════════════════════
# CONFIG HELPERS  —  credentials are NEVER written to disk
# ══════════════════════════════════════════════════════════════════════════════

SAFE_KEYS = {
    'provider', 'country', 'mail', 'logdir',
    'min_window_minutes', 'check_interval_minutes',
    'show_browser', 'show_plot', 'screenshot',
}

def load_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_config(data: dict):
    safe = {k: v for k, v in data.items() if k in SAFE_KEYS}
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(safe, f, indent=2)


# ══════════════════════════════════════════════════════════════════════════════
# CSV HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def read_csv(filepath):
    if not os.path.exists(filepath):
        return []
    with open(filepath, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))

def today_str():
    return date.today().isoformat()


# ══════════════════════════════════════════════════════════════════════════════
# ROUTES — PAGES
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/')
def home():
    return send_from_directory(DATA_DIR, 'dashboard.html')

@app.route('/setup')
def setup_page():
    return send_from_directory(DATA_DIR, 'setup.html')

@app.route('/about')
def about():
    return 'Zonnebrand Solar Dashboard'


# ══════════════════════════════════════════════════════════════════════════════
# ROUTES — CONTROLLER
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/api/start', methods=['POST'])
def api_start():
    data = request.get_json(force=True) or {}
    if not data.get('username') or not data.get('password'):
        return jsonify({'ok': False, 'error': 'SMA username and password are required.'}), 400
    # Save non-sensitive settings
    save_config(data)
    result = _ctrl.start(data)
    code   = 200 if result['ok'] else 400
    return jsonify(result), code

@app.route('/api/stop', methods=['POST'])
def api_stop():
    return jsonify(_ctrl.stop())

@app.route('/api/process-status')
def api_process_status():
    return jsonify(_ctrl.status())

@app.route('/api/logs')
def api_logs():
    n = min(int(request.args.get('n', 100)), 500)
    return jsonify(_ctrl.logs(n))

@app.route('/api/manual-set', methods=['POST'])
def api_manual_set():
    data = request.get_json(force=True) or {}
    pct  = data.get('percent')
    if pct is None:
        return jsonify({'ok': False, 'error': 'percent is required.'}), 400
    try:
        pct = int(pct)
        assert 0 <= pct <= 100
    except (ValueError, AssertionError):
        return jsonify({'ok': False, 'error': 'percent must be 0–100.'}), 400
    if not data.get('username') or not data.get('password'):
        return jsonify({'ok': False, 'error': 'Credentials required for manual override.'}), 400

    result = _ctrl.manual_set(data, pct)
    return jsonify(result), (200 if result['ok'] else 500)

@app.route('/api/config')
def api_config():
    return jsonify(load_config())


# ══════════════════════════════════════════════════════════════════════════════
# ROUTES — DATA
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/api/epex')
def api_epex():
    target_date = request.args.get('date', today_str())
    rows = read_csv(EPEX_CSV)
    seen = {}
    for r in rows:
        if r.get('date') == target_date:
            seen[r['time']] = r
    return jsonify(sorted(seen.values(), key=lambda r: r['time']))

@app.route('/api/epex/dates')
def api_epex_dates():
    rows  = read_csv(EPEX_CSV)
    dates = sorted(set(r['date'] for r in rows if r.get('date')), reverse=True)
    return jsonify(dates)

@app.route('/api/solar')
def api_solar():
    target_date = request.args.get('date', today_str())
    rows = read_csv(SOLAR_CSV)
    return jsonify([r for r in rows if r.get('date') == target_date])

@app.route('/api/status')
def api_status():
    solar_rows   = read_csv(SOLAR_CSV)
    latest_solar = solar_rows[-1] if solar_rows else {}

    now          = datetime.now()
    current_hhmm = now.strftime('%H:%M')
    minute       = (now.minute // 15) * 15
    slot_time    = f'{now.hour:02d}:{minute:02d}'

    seen = {}
    for r in read_csv(EPEX_CSV):
        if r.get('date') == today_str():
            seen[r['time']] = r
    today_epex = sorted(seen.values(), key=lambda r: r['time'])

    current_price = None
    for r in today_epex:
        if r['time'] == slot_time:
            try:   current_price = float(r['price'])
            except (ValueError, KeyError): pass
            break

    prices = []
    for r in today_epex:
        try:   prices.append(float(r['price']))
        except (ValueError, KeyError): pass

    neg_slots = sum(1 for p in prices if p < 0)
    avg_price = sum(prices) / len(prices) if prices else None
    min_price = min(prices) if prices else None
    max_price = max(prices) if prices else None

    upcoming_negative = None
    now_min = now.hour * 60 + now.minute
    for r in today_epex:
        try:
            h, m = map(int, r['time'].split(':'))
            if h * 60 + m >= now_min and float(r['price']) < 0:
                upcoming_negative = r['time']
                break
        except Exception:
            pass

    return jsonify({
        'timestamp':             now.isoformat(),
        'current_time':          current_hhmm,
        'current_slot':          slot_time,
        'current_price_eur_kwh': current_price,
        'solar_target_percent':  int(latest_solar.get('target_percent', 100)) if latest_solar else None,
        'solar_reason':          latest_solar.get('reason', ''),
        'solar_last_updated':    f"{latest_solar.get('date','')} {latest_solar.get('time','')}".strip(),
        'today_stats': {
            'avg_price':      round(avg_price, 5) if avg_price  is not None else None,
            'min_price':      round(min_price, 5) if min_price  is not None else None,
            'max_price':      round(max_price, 5) if max_price  is not None else None,
            'negative_slots': neg_slots,
            'total_slots':    len(prices),
        },
        'upcoming_negative_slot': upcoming_negative,
        'process': _ctrl.status(),
    })

@app.route('/api/history')
def api_history():
    by_date = {}
    for r in read_csv(EPEX_CSV):
        d = r.get('date')
        if not d: continue
        by_date.setdefault(d, [])
        try:   by_date[d].append(float(r['price']))
        except (ValueError, KeyError): pass

    result = []
    for d, prices in sorted(by_date.items()):
        if not prices: continue
        result.append({
            'date':           d,
            'avg':            round(sum(prices) / len(prices), 5),
            'min':            round(min(prices), 5),
            'max':            round(max(prices), 5),
            'negative_slots': sum(1 for p in prices if p < 0),
        })
    return jsonify(result)


# ══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    print()
    print('  ☀  Zonnebrand server starting')
    print(f'     Dashboard : http://0.0.0.0:8000/')
    print(f'     Setup     : http://0.0.0.0:8000/setup')
    print(f'     Data dir  : {os.path.abspath(DATA_DIR)}')
    print()
    # threaded=True is required — the controller loop blocks its thread while
    # sleeping, and Flask needs other threads free to serve requests.
    app.run(host='0.0.0.0', port=8000, debug=False, threaded=True)