from datetime import datetime, timedelta


def format_date(date_str):
    """Formats an ISO date string into a user-friendly relative format."""
    if not date_str:
        return "Unknown date"
    try:
        # Parse ISO string, handling potential timezone info
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))

        # Get current time, making it offset-aware using the parsed dt's timezone
        # Or using local timezone if dt is naive (though ISO usually implies offset)
        if dt.tzinfo:
            now = datetime.now(dt.tzinfo)
        else:
            # Fallback: Assume naive dt refers to local time
            # This might be inaccurate if the source timestamp was UTC but lacks 'Z' or offset
            now = datetime.now()
            # Or assume UTC if naive:
            # dt = dt.replace(tzinfo=timezone.utc)
            # now = datetime.now(timezone.utc)

        today = now.date()
        yesterday = today - timedelta(days=1)
        dt_date = dt.date()  # Compare dates only

        if dt_date == today:
            return f"Today at {dt.strftime('%H:%M')}"
        elif dt_date == yesterday:
            return f"Yesterday at {dt.strftime('%H:%M')}"
        elif dt.year == now.year:
            return dt.strftime("%b %d, %H:%M")  # e.g., Aug 15, 14:30
        else:
            return dt.strftime("%b %d, %Y, %H:%M")  # e.g., Aug 15, 2023, 14:30
    except Exception as e:
        print(f"Date formatting error for '{date_str}': {e}")
        return date_str  # Return original string if format fails
