from datetime import datetime, timezone, date

def get_date_time(format_type = 'today', UTC=False):
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
        # Always use local calendar date (same as date.today()) so the
        # day-change check in the control loop fires at local midnight,
        # not UTC midnight.
        return date.today()