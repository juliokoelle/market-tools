"""
Fetch today's events from Apple Calendar via osascript.

macOS Permission: on first run, macOS will show a dialog asking to allow
Terminal (or the calling app) to access Calendar. Click "Allow".
If blocked: System Settings → Privacy & Security → Calendar → enable Terminal.

Returns one event per line: "HH:MM–HH:MM • Title • Location"
Exits cleanly with empty output if Calendar is unavailable or no events today.
"""

from __future__ import annotations

import datetime
import subprocess
import sys


# Skip read-only/system calendars that are slow or irrelevant for daily notes
_SKIP_CALENDARS = {
    "Siri Suggestions", "Birthdays", "Feiertage in Deutschland",
    "Deutsche Feiertage", "Scheduled Reminders",
}

# AppleScript: collect today's events from user calendars as newline-delimited strings
_APPLESCRIPT = """\
set skipNames to {"Siri Suggestions", "Birthdays", "Feiertage in Deutschland", "Deutsche Feiertage", "Scheduled Reminders"}
set todayStart to current date
set hours of todayStart to 0
set minutes of todayStart to 0
set seconds of todayStart to 0
set todayEnd to todayStart + 86399

set output to ""

tell application "Calendar"
    repeat with cal in every calendar
        if (name of cal) is not in skipNames then
            set evts to (every event of cal whose start date >= todayStart and start date <= todayEnd)
            repeat with ev in evts
                set eStart to start date of ev
                set eEnd to end date of ev
                set eTitle to summary of ev
                set eLoc to ""
                try
                    set eLoc to location of ev
                end try
                set hStart to (hours of eStart) as string
                set mStart to text -2 thru -1 of ("0" & (minutes of eStart) as string)
                set hEnd to (hours of eEnd) as string
                set mEnd to text -2 thru -1 of ("0" & (minutes of eEnd) as string)
                set timeStr to hStart & ":" & mStart & "-" & hEnd & ":" & mEnd
                set output to output & timeStr & "|" & eTitle & "|" & eLoc & linefeed
            end repeat
        end if
    end repeat
end tell

return output
"""


def _format_event(raw_line: str) -> str:
    parts = raw_line.strip().split("|")
    if len(parts) < 2:
        return raw_line.strip()
    time_range = parts[0].strip()
    title = parts[1].strip()
    location = parts[2].strip() if len(parts) > 2 else ""
    if location:
        return f"{time_range} • {title} • {location}"
    return f"{time_range} • {title}"


def fetch_today_events() -> list[str]:
    """Return sorted list of formatted event strings, empty list on any failure."""
    import os
    import time
    import tempfile
    from pathlib import Path

    try:
        # Ensure Calendar is running (open -g = background, no focus steal)
        if os.system("open -g -a Calendar 2>/dev/null") == 0:
            time.sleep(3)

        # Write AppleScript and output to temp files.
        # Avoid Python pipes (capture_output) which can block on macOS TCC-gated apps.
        with tempfile.NamedTemporaryFile(mode="w", suffix=".scpt", delete=False, encoding="utf-8") as f:
            f.write(_APPLESCRIPT)
            scpt_path = f.name
        out_path = scpt_path + ".out"

        try:
            # Run via bash -c so it inherits the shell's TCC Calendar permission
            ret = os.system(f'/bin/bash -c \'osascript "{scpt_path}" > "{out_path}" 2>/dev/null\'')
            if ret != 0 or not os.path.exists(out_path):
                return []
            raw = Path(out_path).read_text(encoding="utf-8")
        finally:
            for p in (scpt_path, out_path):
                try:
                    os.unlink(p)
                except OSError:
                    pass

        lines = [l for l in raw.splitlines() if l.strip()]
        events = [_format_event(l) for l in lines]
        return sorted(events)

    except FileNotFoundError:
        print("[calendar] osascript not found — not running on macOS?", file=sys.stderr)
        return []
    except subprocess.TimeoutExpired:
        print("[calendar] Calendar fetch timed out after 45s.", file=sys.stderr)
        return []
    except Exception as e:
        print(f"[calendar] Unexpected error: {e}", file=sys.stderr)
        return []


if __name__ == "__main__":
    events = fetch_today_events()
    if events:
        for e in events:
            print(e)
    else:
        print("(keine Termine heute oder Kalender nicht verfügbar)")
