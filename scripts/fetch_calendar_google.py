"""
Fetch today's events from Google Calendar via the Google Calendar API.

STATUS: INACTIVE — not yet configured. Apple Calendar (fetch_calendar_today.py) is used instead.

To activate:
1. Enable Google Calendar API in Google Cloud Console
2. Download credentials.json (OAuth2 desktop client)
3. pip install google-auth google-auth-oauthlib google-api-python-client
4. Run once interactively to generate token.json
5. Replace fetch_calendar_today.py calls in create_daily_note.py with this module

Usage (when active):
    python scripts/fetch_calendar_google.py
"""

from __future__ import annotations

import sys


def fetch_today_events() -> list[str]:
    """Return sorted list of formatted event strings. Returns [] — not yet configured."""
    print("[google-calendar] Not configured — using Apple Calendar instead.", file=sys.stderr)
    return []


if __name__ == "__main__":
    events = fetch_today_events()
    if events:
        for e in events:
            print(e)
    else:
        print("(Google Calendar not configured)")
