from flask import Flask, send_from_directory, jsonify, request
import csv
import os
from datetime import datetime, date

app = Flask(__name__)

DATA_DIR = './dashboard'
EPEX_CSV = os.path.join(DATA_DIR, 'epex.csv')
SOLAR_CSV = os.path.join(DATA_DIR, 'zonnebrand.csv')


# ── Helpers ──────────────────────────────────────────────────────────────────

def read_csv(filepath):
    if not os.path.exists(filepath):
        return []
    with open(filepath, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def today_str():
    return date.today().isoformat()


# ── Routes ───────────────────────────────────────────────────────────────────

@app.route('/')
def home():
    return send_from_directory(DATA_DIR, 'dashboard.html')


@app.route('/about')
def about():
    return "Zonnebrand Solar Dashboard"


# GET /api/epex?date=YYYY-MM-DD   (default: today)
@app.route('/api/epex')
def api_epex():
    target_date = request.args.get('date', today_str())
    rows = read_csv(EPEX_CSV)
    filtered = [r for r in rows if r.get('date') == target_date]
    # Deduplicate: keep last entry per (date, time) pair
    seen = {}
    for r in filtered:
        key = r['time']
        seen[key] = r
    result = sorted(seen.values(), key=lambda r: r['time'])
    return jsonify(result)


# GET /api/epex/dates  — list of all dates available in epex.csv
@app.route('/api/epex/dates')
def api_epex_dates():
    rows = read_csv(EPEX_CSV)
    dates = sorted(set(r['date'] for r in rows if r.get('date')), reverse=True)
    return jsonify(dates)


# GET /api/solar?date=YYYY-MM-DD  (default: today)
@app.route('/api/solar')
def api_solar():
    target_date = request.args.get('date', today_str())
    rows = read_csv(SOLAR_CSV)
    filtered = [r for r in rows if r.get('date') == target_date]
    return jsonify(filtered)


# GET /api/status  — latest solar panel state + current EPEX price
@app.route('/api/status')
def api_status():
    # Latest solar entry
    solar_rows = read_csv(SOLAR_CSV)
    latest_solar = solar_rows[-1] if solar_rows else {}

    # Today's EPEX: find slot matching current time
    now = datetime.now()
    current_hhmm = now.strftime('%H:%M')
    # Round down to nearest 15 min
    minute = (now.minute // 15) * 15
    slot_time = f'{now.hour:02d}:{minute:02d}'

    epex_rows = read_csv(EPEX_CSV)
    today_epex = [r for r in epex_rows if r.get('date') == today_str()]

    # Deduplicate
    seen = {}
    for r in today_epex:
        seen[r['time']] = r
    today_epex = sorted(seen.values(), key=lambda r: r['time'])

    current_price = None
    for r in today_epex:
        if r['time'] == slot_time:
            try:
                current_price = float(r['price'])
            except (ValueError, KeyError):
                pass
            break

    # Stats for today
    prices = []
    for r in today_epex:
        try:
            prices.append(float(r['price']))
        except (ValueError, KeyError):
            pass

    negative_slots = sum(1 for p in prices if p < 0)
    avg_price = sum(prices) / len(prices) if prices else None
    min_price = min(prices) if prices else None
    max_price = max(prices) if prices else None

    # Next negative window (upcoming)
    upcoming_negative = None
    now_minutes = now.hour * 60 + now.minute
    for r in today_epex:
        try:
            t = r['time']
            h, m = map(int, t.split(':'))
            slot_minutes = h * 60 + m
            if slot_minutes >= now_minutes and float(r['price']) < 0:
                upcoming_negative = t
                break
        except Exception:
            pass

    return jsonify({
        'timestamp': now.isoformat(),
        'current_time': current_hhmm,
        'current_slot': slot_time,
        'current_price_eur_kwh': current_price,
        'solar_target_percent': int(latest_solar.get('target_percent', 100)) if latest_solar else None,
        'solar_reason': latest_solar.get('reason', ''),
        'solar_last_updated': f"{latest_solar.get('date', '')} {latest_solar.get('time', '')}".strip(),
        'today_stats': {
            'avg_price': round(avg_price, 5) if avg_price is not None else None,
            'min_price': round(min_price, 5) if min_price is not None else None,
            'max_price': round(max_price, 5) if max_price is not None else None,
            'negative_slots': negative_slots,
            'total_slots': len(prices),
        },
        'upcoming_negative_slot': upcoming_negative,
    })


# GET /api/history  — daily summary stats for all dates (for heatmap)
@app.route('/api/history')
def api_history():
    rows = read_csv(EPEX_CSV)
    # Group by date
    by_date = {}
    for r in rows:
        d = r.get('date')
        if not d:
            continue
        by_date.setdefault(d, [])
        try:
            by_date[d].append(float(r['price']))
        except (ValueError, KeyError):
            pass

    result = []
    for d, prices in sorted(by_date.items()):
        if not prices:
            continue
        result.append({
            'date': d,
            'avg': round(sum(prices) / len(prices), 5),
            'min': round(min(prices), 5),
            'max': round(max(prices), 5),
            'negative_slots': sum(1 for p in prices if p < 0),
        })
    return jsonify(result)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)