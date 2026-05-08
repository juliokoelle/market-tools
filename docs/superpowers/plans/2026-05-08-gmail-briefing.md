# Gmail Briefing Ingestion — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace LLM-generated daily briefing with Gmail IMAP ingestion of two morningcrunch.de newsletters, combined as Markdown and synced to Obsidian/GitHub via the existing sync_to_brain pipeline.

**Architecture:** `fetch_gmail_briefing.py` handles IMAP auth, email search, HTML→Markdown conversion, and combining both newsletters. `run_gmail_briefing.py` is the cron entry point that saves outputs and calls `sync_to_brain`. A new Render cron service triggers at 06:15 UTC. `POST /briefing/generate` is disabled with 410 and the generate buttons are removed from the frontend.

**Tech Stack:** Python stdlib `imaplib` + `email`, `html2text` (HTML→MD), `python-dotenv`, existing `sync_to_brain.py`, FastAPI `TestClient` for API tests.

---

## File Map

| File | Status | Responsibility |
|---|---|---|
| `scripts/fetch_gmail_briefing.py` | CREATE | IMAP connect, email search, HTML→MD, combine |
| `scripts/run_gmail_briefing.py` | CREATE | Cron entry point: env check, fetch, save, sync |
| `tests/test_fetch_gmail_briefing.py` | CREATE | Unit tests for all fetch_gmail_briefing functions |
| `tests/test_run_gmail_briefing.py` | CREATE | Unit tests for run pipeline |
| `requirements.txt` | MODIFY | +html2text, +httpx |
| `render.yaml` | MODIFY | Add gmail-briefing-cron service |
| `scripts/api.py` | MODIFY | Disable POST /briefing/generate + POST /generate-briefing |
| `frontend/index.html` | MODIFY | Remove generate buttons + generateBriefing() JS |

---

### Task 1: Add dependencies

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Add html2text and httpx to requirements.txt**

Full final file:
```
fastapi
uvicorn[standard]
yfinance
pandas
numpy
requests
python-dotenv
anthropic
openai
feedparser
weasyprint
markdown
pyyaml
html2text
httpx
```

- [ ] **Step 2: Install into venv**

```bash
pip install html2text httpx
```

Expected: `Successfully installed html2text-...` and `Successfully installed httpx-...`

- [ ] **Step 3: Verify import**

```bash
python -c "import html2text; print(html2text.__version__)"
```

Expected: prints a version string (e.g. `2020.1.16`)

- [ ] **Step 4: Commit**

```bash
git add requirements.txt
git commit -m "chore(deps): add html2text and httpx"
```

---

### Task 2: HTML→Markdown conversion helpers (TDD)

**Files:**
- Create: `tests/test_fetch_gmail_briefing.py`
- Create: `scripts/fetch_gmail_briefing.py` (skeleton + conversion only)

- [ ] **Step 1: Create test file with failing conversion tests**

Create `tests/test_fetch_gmail_briefing.py`:

```python
"""Unit tests for Gmail briefing fetcher."""
import email as email_lib
import pytest


def test_html_to_markdown_converts_headings():
    from scripts.fetch_gmail_briefing import _html_to_markdown
    html = "<h2>Markets Today</h2><p>Gold rose 1.2% to $3,400/oz.</p>"
    result = _html_to_markdown(html)
    assert "## Markets Today" in result
    assert "Gold rose 1.2% to $3,400/oz." in result


def test_html_to_markdown_ignores_images():
    from scripts.fetch_gmail_briefing import _html_to_markdown
    html = "<p>Text content</p><img src='track.gif' />"
    result = _html_to_markdown(html)
    assert "track.gif" not in result
    assert "Text content" in result


def test_html_to_markdown_preserves_umlauts():
    from scripts.fetch_gmail_briefing import _html_to_markdown
    html = "<p>Märkte in Frankfurt stiegen um 0,5%.</p>"
    result = _html_to_markdown(html)
    assert "Märkte" in result
    assert "Frankfurt" in result


def test_html_to_markdown_preserves_bold():
    from scripts.fetch_gmail_briefing import _html_to_markdown
    html = "<p>DAX <strong>+1.2%</strong> today.</p>"
    result = _html_to_markdown(html)
    assert "**+1.2%**" in result


def test_clean_markdown_collapses_blank_lines():
    from scripts.fetch_gmail_briefing import _clean_markdown
    md = "Line 1\n\n\n\n\nLine 2"
    result = _clean_markdown(md)
    assert "\n\n\n" not in result
    assert "Line 1" in result
    assert "Line 2" in result


def test_clean_markdown_strips_abmelden():
    from scripts.fetch_gmail_briefing import _clean_markdown
    md = "Wichtige Nachricht hier.\n\nAbmelden von diesem Newsletter."
    result = _clean_markdown(md)
    assert "Wichtige Nachricht" in result
    assert "Abmelden" not in result


def test_clean_markdown_strips_unsubscribe_and_copyright():
    from scripts.fetch_gmail_briefing import _clean_markdown
    md = "Market update.\n\nUnsubscribe from this list.\n© 2026 MorningCrunch"
    result = _clean_markdown(md)
    assert "Market update." in result
    assert "Unsubscribe" not in result
    assert "© 2026" not in result


def test_clean_markdown_strips_impressum():
    from scripts.fetch_gmail_briefing import _clean_markdown
    md = "Gute Neuigkeiten.\n\nImpressum | Datenschutz"
    result = _clean_markdown(md)
    assert "Gute Neuigkeiten." in result
    assert "Impressum" not in result


def test_clean_markdown_trims_whitespace():
    from scripts.fetch_gmail_briefing import _clean_markdown
    md = "\n\n  Content here.  \n\n"
    result = _clean_markdown(md)
    assert result == "Content here."
```

- [ ] **Step 2: Run tests — expect ModuleNotFoundError**

```bash
python -m pytest tests/test_fetch_gmail_briefing.py -v 2>&1 | head -15
```

Expected: `ModuleNotFoundError: No module named 'scripts.fetch_gmail_briefing'`

- [ ] **Step 3: Create scripts/fetch_gmail_briefing.py**

Create `scripts/fetch_gmail_briefing.py`:

```python
"""
Gmail briefing fetcher — IMAP + App Password.

Fetches today's emails from two MorningCrunch newsletters, converts HTML bodies
to Markdown, and returns a combined briefing string.

Env vars required:
    GMAIL_USERNAME      — full Gmail address (e.g. juliokoelle@gmail.com)
    GMAIL_APP_PASSWORD  — 16-char Google App Password (no spaces)
"""

from __future__ import annotations

import email as email_lib
import imaplib
import logging
import os
import re
from datetime import datetime, timezone

import html2text as ht

log = logging.getLogger(__name__)

IMAP_HOST = "imap.gmail.com"
IMAP_PORT = 993

BRIEFING_SENDERS = [
    {
        "from":  "markets@m.morningcrunch.de",
        "label": "MarketsXrunch — Markets & Finance",
    },
    {
        "from":  "deals@m2.morningcrunch.de",
        "label": "DealsXrunch — Deals & Business",
    },
]

_FOOTER_RE = re.compile(
    r"(Abmelde|Unsubscribe|©|\bImpressum\b|Datenschutz)",
    re.IGNORECASE,
)


def _html_to_markdown(html: str) -> str:
    """Convert HTML email body to structured Markdown."""
    h = ht.HTML2Text()
    h.ignore_links  = False
    h.ignore_images = True
    h.body_width    = 0
    h.unicode_snob  = True
    return h.handle(html)


def _clean_markdown(md: str) -> str:
    """Strip footer boilerplate and collapse excessive blank lines."""
    lines = [line for line in md.splitlines() if not _FOOTER_RE.search(line)]
    text  = "\n".join(lines)
    text  = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
```

- [ ] **Step 4: Run tests — expect 9 passed**

```bash
python -m pytest tests/test_fetch_gmail_briefing.py -v 2>&1 | tail -15
```

Expected: `9 passed`

- [ ] **Step 5: Commit**

```bash
git add scripts/fetch_gmail_briefing.py tests/test_fetch_gmail_briefing.py
git commit -m "feat(gmail): html-to-markdown conversion helpers"
```

---

### Task 3: IMAP email fetch logic (TDD)

**Files:**
- Modify: `tests/test_fetch_gmail_briefing.py` (append)
- Modify: `scripts/fetch_gmail_briefing.py` (append)

- [ ] **Step 1: Append IMAP tests to test file**

Append to `tests/test_fetch_gmail_briefing.py`:

```python
# ── IMAP fetch tests ─────────────────────────────────────────────────────────

def test_extract_html_from_simple_html_message():
    from email.mime.text import MIMEText
    from scripts.fetch_gmail_briefing import _extract_html
    raw = MIMEText("<h2>Gold +1%</h2>", "html", "utf-8").as_bytes()
    msg = email_lib.message_from_bytes(raw)
    result = _extract_html(msg)
    assert result is not None
    assert "Gold" in result


def test_extract_html_from_multipart_message():
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from scripts.fetch_gmail_briefing import _extract_html
    msg = MIMEMultipart("alternative")
    msg.attach(MIMEText("Plain text version", "plain", "utf-8"))
    msg.attach(MIMEText("<p>HTML version</p>", "html", "utf-8"))
    result = _extract_html(email_lib.message_from_bytes(msg.as_bytes()))
    assert result is not None
    assert "HTML version" in result


def test_extract_html_returns_none_for_plain_only():
    from email.mime.text import MIMEText
    from scripts.fetch_gmail_briefing import _extract_html
    msg = email_lib.message_from_bytes(
        MIMEText("Plain only", "plain", "utf-8").as_bytes()
    )
    result = _extract_html(msg)
    assert result is None


def test_fetch_email_html_returns_none_when_search_empty():
    from unittest.mock import MagicMock
    from scripts.fetch_gmail_briefing import _fetch_email_html
    conn = MagicMock()
    conn.select.return_value = ("OK", [b"1"])
    conn.search.return_value = ("OK", [b""])  # no results
    result = _fetch_email_html(conn, "markets@m.morningcrunch.de")
    assert result is None


def test_fetch_email_html_returns_html_body():
    from email.mime.text import MIMEText
    from unittest.mock import MagicMock
    from scripts.fetch_gmail_briefing import _fetch_email_html
    raw  = MIMEText("<h2>Markets Today</h2>", "html", "utf-8").as_bytes()
    conn = MagicMock()
    conn.select.return_value = ("OK", [b"1"])
    conn.search.return_value = ("OK", [b"42"])
    conn.fetch.return_value  = ("OK", [(b"42 (RFC822 {256})", raw)])
    result = _fetch_email_html(conn, "markets@m.morningcrunch.de")
    assert result is not None
    assert "Markets Today" in result


def test_fetch_email_html_takes_last_uid_when_multiple():
    """When multiple UIDs match, fetch the last (most recent) one."""
    from email.mime.text import MIMEText
    from unittest.mock import MagicMock
    from scripts.fetch_gmail_briefing import _fetch_email_html
    raw  = MIMEText("<p>Latest</p>", "html", "utf-8").as_bytes()
    conn = MagicMock()
    conn.select.return_value = ("OK", [b"5"])
    conn.search.return_value = ("OK", [b"10 11 12"])
    conn.fetch.return_value  = ("OK", [(b"12 (RFC822 {100})", raw)])
    _fetch_email_html(conn, "markets@m.morningcrunch.de")
    conn.fetch.assert_called_once_with(b"12", "(RFC822)")
```

- [ ] **Step 2: Run new tests — expect failures**

```bash
python -m pytest tests/test_fetch_gmail_briefing.py -v -k "extract or fetch_email" 2>&1 | tail -12
```

Expected: all 6 new tests fail with `ImportError` or `AttributeError`

- [ ] **Step 3: Append IMAP functions to fetch_gmail_briefing.py**

Append after `_clean_markdown`:

```python
def _extract_html(msg: email_lib.message.Message) -> str | None:
    """Walk MIME tree and return the first text/html payload as a decoded string."""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                charset = part.get_content_charset() or "utf-8"
                return part.get_payload(decode=True).decode(charset, errors="replace")
    elif msg.get_content_type() == "text/html":
        charset = msg.get_content_charset() or "utf-8"
        return msg.get_payload(decode=True).decode(charset, errors="replace")
    return None


def _fetch_email_html(conn: imaplib.IMAP4_SSL, sender: str) -> str | None:
    """Search INBOX (fallback: All Mail) for today's email from sender.

    Returns the HTML body of the most recent match, or None if not found.
    """
    today_str = datetime.now(timezone.utc).strftime("%d-%b-%Y")  # e.g. "08-May-2026"
    criteria  = f'(FROM "{sender}" SINCE {today_str})'

    for mailbox in ("INBOX", '"[Gmail]/All Mail"'):
        typ, _ = conn.select(mailbox)
        if typ != "OK":
            continue

        typ, data = conn.search(None, criteria)
        if typ != "OK" or not data[0]:
            continue

        uids = data[0].split()
        if not uids:
            continue

        uid = uids[-1]  # most recent
        typ, msg_data = conn.fetch(uid, "(RFC822)")
        if typ != "OK":
            log.warning("[gmail] fetch failed for UID %s from %s", uid, sender)
            continue

        raw = msg_data[0][1]
        msg = email_lib.message_from_bytes(raw)
        html = _extract_html(msg)
        if html is None:
            log.warning("[gmail] No HTML part found in email from %s", sender)
        return html

    return None


def _connect_imap() -> imaplib.IMAP4_SSL:
    """Open an authenticated IMAP connection. Raises on any failure."""
    username = os.environ["GMAIL_USERNAME"]
    password = os.environ["GMAIL_APP_PASSWORD"]
    conn = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
    conn.login(username, password)
    return conn
```

- [ ] **Step 4: Run all fetch tests — expect 15 passed**

```bash
python -m pytest tests/test_fetch_gmail_briefing.py -v 2>&1 | tail -10
```

Expected: `15 passed`

- [ ] **Step 5: Commit**

```bash
git add scripts/fetch_gmail_briefing.py tests/test_fetch_gmail_briefing.py
git commit -m "feat(gmail): imap email fetch and html mime extraction"
```

---

### Task 4: Public `fetch_today_briefing()` (TDD)

**Files:**
- Modify: `tests/test_fetch_gmail_briefing.py` (append)
- Modify: `scripts/fetch_gmail_briefing.py` (append)

- [ ] **Step 1: Append public API tests**

Append to `tests/test_fetch_gmail_briefing.py`:

```python
# ── fetch_today_briefing public API ──────────────────────────────────────────

def test_fetch_today_briefing_returns_none_when_no_emails():
    from unittest.mock import MagicMock, patch
    from scripts.fetch_gmail_briefing import fetch_today_briefing
    mock_conn = MagicMock()
    with patch("scripts.fetch_gmail_briefing._connect_imap", return_value=mock_conn), \
         patch("scripts.fetch_gmail_briefing._fetch_email_html", return_value=None):
        result = fetch_today_briefing()
    assert result is None
    mock_conn.logout.assert_called_once()


def test_fetch_today_briefing_combines_both_sections():
    from unittest.mock import MagicMock, patch
    from scripts.fetch_gmail_briefing import fetch_today_briefing
    mock_conn = MagicMock()

    def fake_fetch(conn, sender):
        if "markets" in sender:
            return "<h2>Gold +1%</h2><p>DAX up.</p>"
        return "<h2>SAP Deal</h2><p>Acquisition closed.</p>"

    with patch("scripts.fetch_gmail_briefing._connect_imap", return_value=mock_conn), \
         patch("scripts.fetch_gmail_briefing._fetch_email_html", side_effect=fake_fetch):
        result = fetch_today_briefing()

    assert result is not None
    assert "MarketsXrunch" in result
    assert "DealsXrunch" in result
    assert result.index("MarketsXrunch") < result.index("DealsXrunch")
    assert "---" in result  # section separator


def test_fetch_today_briefing_partial_returns_content():
    """Only one email found — return partial content, not None."""
    from unittest.mock import MagicMock, patch
    from scripts.fetch_gmail_briefing import fetch_today_briefing
    mock_conn = MagicMock()

    def fake_fetch(conn, sender):
        return "<p>Markets content</p>" if "markets" in sender else None

    with patch("scripts.fetch_gmail_briefing._connect_imap", return_value=mock_conn), \
         patch("scripts.fetch_gmail_briefing._fetch_email_html", side_effect=fake_fetch):
        result = fetch_today_briefing()

    assert result is not None
    assert "MarketsXrunch" in result
    assert "DealsXrunch" not in result


def test_fetch_today_briefing_closes_connection_on_error():
    from unittest.mock import MagicMock, patch
    from scripts.fetch_gmail_briefing import fetch_today_briefing
    mock_conn = MagicMock()

    with patch("scripts.fetch_gmail_briefing._connect_imap", return_value=mock_conn), \
         patch("scripts.fetch_gmail_briefing._fetch_email_html",
               side_effect=RuntimeError("boom")):
        with pytest.raises(RuntimeError):
            fetch_today_briefing()

    mock_conn.logout.assert_called_once()
```

- [ ] **Step 2: Run new tests — expect failures**

```bash
python -m pytest tests/test_fetch_gmail_briefing.py -v -k "today_briefing" 2>&1 | tail -10
```

Expected: failures with `ImportError` — `fetch_today_briefing` not defined

- [ ] **Step 3: Append fetch_today_briefing to fetch_gmail_briefing.py**

Append after `_connect_imap`:

```python
def fetch_today_briefing() -> str | None:
    """Fetch today's newsletters from both MorningCrunch senders via IMAP.

    Returns combined Markdown string, or None if neither email was found.
    """
    conn = _connect_imap()
    sections: list[str] = []

    try:
        for sender_cfg in BRIEFING_SENDERS:
            sender = sender_cfg["from"]
            label  = sender_cfg["label"]
            html = _fetch_email_html(conn, sender)
            if html is None:
                log.warning("[gmail] No email from %s today — skipping section.", sender)
                continue
            md = _clean_markdown(_html_to_markdown(html))
            sections.append(f"## {label}\n\n{md}")
            log.info("[gmail] Fetched %d chars from %s.", len(md), sender)
    finally:
        try:
            conn.logout()
        except Exception:
            pass

    if not sections:
        return None

    return "\n\n---\n\n".join(sections)
```

- [ ] **Step 4: Run all fetch tests — expect 19 passed**

```bash
python -m pytest tests/test_fetch_gmail_briefing.py -v 2>&1 | tail -10
```

Expected: `19 passed`

- [ ] **Step 5: Commit**

```bash
git add scripts/fetch_gmail_briefing.py tests/test_fetch_gmail_briefing.py
git commit -m "feat(gmail): public fetch_today_briefing combining both newsletters"
```

---

### Task 5: `run_gmail_briefing.py` pipeline (TDD)

**Files:**
- Create: `tests/test_run_gmail_briefing.py`
- Create: `scripts/run_gmail_briefing.py`

- [ ] **Step 1: Create failing pipeline tests**

Create `tests/test_run_gmail_briefing.py`:

```python
"""Unit tests for the Gmail briefing pipeline entry point."""
import pytest


def test_check_env_exits_when_both_vars_missing(monkeypatch):
    monkeypatch.delenv("GMAIL_USERNAME",     raising=False)
    monkeypatch.delenv("GMAIL_APP_PASSWORD", raising=False)
    from scripts.run_gmail_briefing import _check_env
    with pytest.raises(SystemExit) as exc:
        _check_env()
    assert exc.value.code == 1


def test_check_env_exits_when_one_var_missing(monkeypatch):
    monkeypatch.setenv("GMAIL_USERNAME",     "test@gmail.com")
    monkeypatch.delenv("GMAIL_APP_PASSWORD", raising=False)
    from scripts.run_gmail_briefing import _check_env
    with pytest.raises(SystemExit) as exc:
        _check_env()
    assert exc.value.code == 1


def test_check_env_passes_when_both_set(monkeypatch):
    monkeypatch.setenv("GMAIL_USERNAME",     "test@gmail.com")
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "test-pass-1234")
    from scripts.run_gmail_briefing import _check_env
    _check_env()  # must not raise


def test_run_exits_zero_when_no_emails(monkeypatch):
    monkeypatch.setenv("GMAIL_USERNAME",     "test@gmail.com")
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "test-pass-1234")
    import scripts.run_gmail_briefing as runner
    monkeypatch.setattr(runner, "fetch_today_briefing", lambda: None)
    with pytest.raises(SystemExit) as exc:
        runner.run()
    assert exc.value.code == 0


def test_run_saves_latest_and_archive(monkeypatch, tmp_path):
    monkeypatch.setenv("GMAIL_USERNAME",     "test@gmail.com")
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "test-pass-1234")
    synced: list = []
    import scripts.run_gmail_briefing as runner
    monkeypatch.setattr(runner, "OUTPUTS_DIR",          tmp_path)
    monkeypatch.setattr(runner, "LATEST_FILE",          tmp_path / "latest-briefing.md")
    monkeypatch.setattr(runner, "fetch_today_briefing", lambda: "## MarketsXrunch\n\nGold +1%.")
    monkeypatch.setattr(runner, "brain_sync",           lambda d, c: synced.append((d, c)))
    monkeypatch.setattr(runner, "today",                lambda: "2026-05-08")
    runner.run()
    latest  = (tmp_path / "latest-briefing.md").read_text(encoding="utf-8")
    archive = (tmp_path / "2026-05-08-briefing.md").read_text(encoding="utf-8")
    assert "# Daily Briefing — 2026-05-08" in latest
    assert "MarketsXrunch" in latest
    assert latest == archive
    assert len(synced) == 1
    assert synced[0][0] == "2026-05-08"
    assert "MarketsXrunch" in synced[0][1]


def test_run_continues_when_brain_sync_fails(monkeypatch, tmp_path):
    """brain_sync failure must not crash the pipeline."""
    monkeypatch.setenv("GMAIL_USERNAME",     "test@gmail.com")
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "test-pass-1234")
    import scripts.run_gmail_briefing as runner
    monkeypatch.setattr(runner, "OUTPUTS_DIR",          tmp_path)
    monkeypatch.setattr(runner, "LATEST_FILE",          tmp_path / "latest-briefing.md")
    monkeypatch.setattr(runner, "fetch_today_briefing", lambda: "## Section\n\nContent.")
    monkeypatch.setattr(runner, "brain_sync",
                        lambda d, c: (_ for _ in ()).throw(RuntimeError("sync failed")))
    monkeypatch.setattr(runner, "today",                lambda: "2026-05-08")
    runner.run()  # must not raise
    assert (tmp_path / "latest-briefing.md").exists()
```

- [ ] **Step 2: Run tests — expect ModuleNotFoundError**

```bash
python -m pytest tests/test_run_gmail_briefing.py -v 2>&1 | head -10
```

Expected: `ModuleNotFoundError: No module named 'scripts.run_gmail_briefing'`

- [ ] **Step 3: Create scripts/run_gmail_briefing.py**

Create `scripts/run_gmail_briefing.py`:

```python
"""
Gmail briefing pipeline — designed to run as a Render Cron Job at 06:15 UTC.

Steps:
  1. Verify GMAIL_USERNAME and GMAIL_APP_PASSWORD are set
  2. Fetch today's newsletters from Gmail via IMAP
  3. Save to outputs/latest-briefing.md + outputs/YYYY-MM-DD-briefing.md
  4. Sync to julio-brain via GitHub API

Run locally:
    python -m scripts.run_gmail_briefing

Required environment variables:
    GMAIL_USERNAME
    GMAIL_APP_PASSWORD
    GITHUB_TOKEN           (for sync_to_brain)
    JULIO_BRAIN_OWNER      (default: juliokoelle)
    JULIO_BRAIN_REPO_NAME  (default: julio-brain)
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from scripts.fetch_gmail_briefing import fetch_today_briefing  # noqa: E402
from scripts.sync_to_brain import sync as brain_sync           # noqa: E402
from scripts.utils import today                                 # noqa: E402

OUTPUTS_DIR = Path("outputs")
LATEST_FILE = OUTPUTS_DIR / "latest-briefing.md"


def _log(msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"[{ts}] {msg}", flush=True)


def _check_env() -> None:
    missing = [v for v in ("GMAIL_USERNAME", "GMAIL_APP_PASSWORD") if not os.getenv(v)]
    if missing:
        _log(f"ERROR — missing env vars: {', '.join(missing)}")
        sys.exit(1)


def run() -> None:
    _check_env()

    run_date = today()
    _log(f"=== Gmail briefing pipeline started for {run_date} ===")

    _log("Fetching emails from Gmail…")
    briefing_md = fetch_today_briefing()

    if briefing_md is None:
        _log("No briefing emails found today — exiting without overwrite.")
        sys.exit(0)

    header  = f"# Daily Briefing — {run_date}\n\n"
    content = header + briefing_md

    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    LATEST_FILE.write_text(content, encoding="utf-8")
    _log(f"Saved latest  → {LATEST_FILE}")

    archive = OUTPUTS_DIR / f"{run_date}-briefing.md"
    archive.write_text(content, encoding="utf-8")
    _log(f"Saved archive → {archive}")

    try:
        brain_sync(run_date, content)
        _log("Synced to julio-brain.")
    except Exception as e:
        _log(f"Brain sync failed (non-blocking): {e}")

    _log("=== Pipeline complete. ===")


if __name__ == "__main__":
    run()
```

- [ ] **Step 4: Run pipeline tests — expect 6 passed**

```bash
python -m pytest tests/test_run_gmail_briefing.py -v 2>&1 | tail -12
```

Expected: `6 passed`

- [ ] **Step 5: Run full test suite — no regressions**

```bash
python -m pytest tests/ -v 2>&1 | tail -10
```

Expected: all existing tests still pass

- [ ] **Step 6: Commit**

```bash
git add scripts/run_gmail_briefing.py tests/test_run_gmail_briefing.py
git commit -m "feat(gmail): run_gmail_briefing pipeline entry point"
```

---

### Task 6: Render cron service

**Files:**
- Modify: `render.yaml`

- [ ] **Step 1: Append cron service to render.yaml**

Full final `render.yaml`:

```yaml
services:
  - type: web
    name: market-tools-backend
    env: python
    plan: free
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn scripts.api:app --host 0.0.0.0 --port $PORT
    autoDeploy: true

  - type: web
    name: market-tools-frontend
    env: static
    plan: free
    staticPublishPath: ./frontend
    buildCommand: ""
    autoDeploy: true

  - type: cron
    name: gmail-briefing-cron
    env: python
    plan: free
    schedule: "15 6 * * *"
    buildCommand: pip install -r requirements.txt
    startCommand: python -m scripts.run_gmail_briefing
```

- [ ] **Step 2: Verify YAML syntax**

```bash
python -c "import yaml; yaml.safe_load(open('render.yaml')); print('YAML valid')"
```

Expected: `YAML valid`

- [ ] **Step 3: Commit**

```bash
git add render.yaml
git commit -m "feat(render): add gmail-briefing-cron at 06:15 UTC daily"
```

---

### Task 7: Disable POST /briefing/generate (TDD)

**Files:**
- Create: `tests/test_api_briefing_disabled.py`
- Modify: `scripts/api.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_api_briefing_disabled.py`:

```python
"""Verify that POST /briefing/generate and legacy endpoint return 410 Gone."""
from fastapi.testclient import TestClient


def _client():
    from scripts.api import app
    return TestClient(app)


def test_briefing_generate_returns_410():
    resp = _client().post("/briefing/generate")
    assert resp.status_code == 410
    assert resp.json()["error"] == "generation_disabled"


def test_briefing_generate_returns_410_for_openai():
    resp = _client().post("/briefing/generate?provider=openai")
    assert resp.status_code == 410


def test_generate_briefing_legacy_returns_410():
    resp = _client().post("/generate-briefing")
    assert resp.status_code == 410
    assert resp.json()["error"] == "generation_disabled"
```

- [ ] **Step 2: Run test — expect failure (currently returns 200/500)**

```bash
python -m pytest tests/test_api_briefing_disabled.py -v 2>&1 | tail -10
```

Expected: tests fail — status code is not 410

- [ ] **Step 3: Replace briefing_generate body in api.py**

In `scripts/api.py`, find the `briefing_generate` function (starts with `@app.post("/briefing/generate")`).
Replace the entire function body with:

```python
@app.post("/briefing/generate")
def briefing_generate(provider: str = Query("anthropic")):
    raise HTTPException(
        status_code=410,
        detail={
            "error": "generation_disabled",
            "message": "Briefing wird täglich automatisch per E-Mail bezogen.",
        },
    )
```

- [ ] **Step 4: Replace generate_briefing_legacy body in api.py**

Find `@app.post("/generate-briefing")` and replace its function body:

```python
@app.post("/generate-briefing")
def generate_briefing_legacy():
    """Legacy endpoint — disabled, use Gmail pipeline instead."""
    raise HTTPException(
        status_code=410,
        detail={
            "error": "generation_disabled",
            "message": "Briefing wird täglich automatisch per E-Mail bezogen.",
        },
    )
```

- [ ] **Step 5: Run disabled endpoint tests — expect 3 passed**

```bash
python -m pytest tests/test_api_briefing_disabled.py -v 2>&1 | tail -10
```

Expected: `3 passed`

- [ ] **Step 6: Run full test suite — no regressions**

```bash
python -m pytest tests/ -v 2>&1 | tail -10
```

Expected: all tests pass

- [ ] **Step 7: Commit**

```bash
git add scripts/api.py tests/test_api_briefing_disabled.py
git commit -m "feat(api): disable POST /briefing/generate — returns 410 Gone"
```

---

### Task 8: Remove generate buttons from frontend

**Files:**
- Modify: `frontend/index.html`

- [ ] **Step 1: Replace button group HTML (lines 1601–1608)**

Find this block:

```html
      <div style="display:flex; flex-direction:column; align-items:flex-end; gap:6px;">
        <div style="display:flex; gap:8px;">
          <button id="generatePremiumBtn" class="btn-primary" onclick="generateBriefing('anthropic')">Generate Premium</button>
          <button id="generateQuickBtn"   class="btn-secondary" onclick="generateBriefing('openai')">Generate Quick</button>
        </div>
        <span id="generateStatus" style="font-size:0.75rem; color:var(--muted);"></span>
        <span id="costCounter"    style="font-size:0.72rem; color:var(--faint);"></span>
      </div>
```

Replace with:

```html
      <div style="display:flex; flex-direction:column; align-items:flex-end; gap:6px;">
        <span style="font-size:0.75rem; color:var(--faint);">Briefing arrives daily at ~08:15 (CEST)</span>
      </div>
```

- [ ] **Step 2: Update briefingContent default text (line 1611)**

Find:
```html
      <div id="briefingContent" style="font-size:0.9rem; color:var(--muted);">Ready to generate. Briefings are saved to julio-brain.</div>
```

Replace with:
```html
      <div id="briefingContent" style="font-size:0.9rem; color:var(--muted);">Select a date from the archive to read the briefing.</div>
```

- [ ] **Step 3: Remove generateBriefing JS function (lines 2703–2747)**

Find and delete the entire function:

```javascript
async function generateBriefing(provider = 'anthropic') {
  const premiumBtn = document.getElementById('generatePremiumBtn');
  // ... through closing brace on line 2747
}
```

Delete everything from `async function generateBriefing` through and including the closing `}`.

- [ ] **Step 4: Remove orphaned CSS (lines 555–573)**

Find and delete these CSS rules:

```css
    #generateBtn {
      ...
    }
    #generateBtn:hover:not(:disabled) { background: var(--accent-lt); }
    #generateBtn:disabled { opacity: 0.5; cursor: not-allowed; }
    #generateStatus { font-size: 0.72rem; color: var(--faint); }
    #generateStatus.ok    { color: var(--green-dk); }
    #generateStatus.error { color: var(--red-dk); }
```

- [ ] **Step 5: Smoke-test in browser**

```bash
open frontend/index.html
```

Open browser DevTools → Console. Expected: no JavaScript errors on page load. Navigate to the Briefing view — the "Generate Premium / Generate Quick" buttons should not appear; the schedule info text should show instead.

- [ ] **Step 6: Commit**

```bash
git add frontend/index.html
git commit -m "feat(frontend): remove LLM generate buttons, show daily schedule info"
```

---

## Post-implementation checklist

- [ ] Set `GMAIL_USERNAME`, `GMAIL_APP_PASSWORD`, `GITHUB_TOKEN`, `JULIO_BRAIN_OWNER`, `JULIO_BRAIN_REPO_NAME` on the `gmail-briefing-cron` service in Render dashboard
- [ ] Confirm Gmail IMAP is enabled (Gmail Settings → Forwarding and POP/IMAP)
- [ ] Confirm App Password exists (Google Account → Security → App passwords)
- [ ] Trigger a manual test run: `python -m scripts.run_gmail_briefing` (requires valid credentials in `.env`)
- [ ] Verify briefing appears in `outputs/` and in `julio-brain/10_Daily/`
