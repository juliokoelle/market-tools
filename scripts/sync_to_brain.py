"""
Syncs a generated briefing to the julio-brain GitHub repo via Contents API.

On Render (GITHUB_TOKEN + JULIO_BRAIN_OWNER + JULIO_BRAIN_REPO_NAME set):
  - PUTs file to GitHub API: PUT /repos/{owner}/{repo}/contents/10_Daily/{date}.md
  - GETs existing file first to retrieve SHA (required for updates)

Locally (no GITHUB_TOKEN):
  - Falls back to local git commit in ~/projects/julio-brain
  - Skips push silently if no token

Non-blocking: caller wraps in try/except. Sync failure never crashes briefing save.
"""

from __future__ import annotations

import base64
import logging
import os
import subprocess
from collections.abc import Callable
from pathlib import Path

import requests

log = logging.getLogger(__name__)

BRAIN_DIR = Path.home() / "projects" / "julio-brain"
DAILY_DIR = BRAIN_DIR / "10_Daily"


def _gh_config() -> tuple[str, str, str] | None:
    """Returns (token, owner, repo_name) or None if GITHUB_TOKEN is not set."""
    token = os.getenv("GITHUB_TOKEN", "").strip()
    if not token:
        return None
    owner = os.getenv("JULIO_BRAIN_OWNER", "juliokoelle").strip()
    repo  = os.getenv("JULIO_BRAIN_REPO_NAME", "julio-brain").strip()
    return token, owner, repo


def _github_put(token: str, owner: str, repo: str, run_date: str, content: str) -> None:
    """Create or update 10_Daily/{run_date}.md via GitHub Contents API."""
    api_url = (
        f"https://api.github.com/repos/{owner}/{repo}"
        f"/contents/10_Daily/{run_date}.md"
    )
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    # GET existing file to retrieve SHA (required for updates, omitted for creates)
    sha: str | None = None
    try:
        get_resp = requests.get(api_url, headers=headers, timeout=10)
        if get_resp.status_code == 200:
            data = get_resp.json()
            sha = data.get("sha")
            existing_b64 = data.get("content", "").replace("\n", "")
            existing_text = base64.b64decode(existing_b64).decode("utf-8")
            if existing_text.strip() == content.strip():
                log.info("[brain] GitHub content unchanged — skipping PUT for %s.", run_date)
                return
    except requests.RequestException as e:
        log.warning("[brain] GitHub GET for SHA failed: %s", e)

    body: dict = {
        "message": f"briefing: daily briefing {run_date}",
        "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
        "branch": "main",
    }
    if sha:
        body["sha"] = sha

    put_resp = requests.put(api_url, headers=headers, json=body, timeout=30)
    if put_resp.status_code in (200, 201):
        action = "updated" if sha else "created"
        log.info("[brain] GitHub push OK — %s %s.md.", action, run_date)
    else:
        log.warning(
            "[brain] GitHub PUT failed: HTTP %s — %s",
            put_resp.status_code,
            put_resp.text[:300],
        )


def _local_commit(run_date: str, content: str) -> None:
    """Write briefing to local julio-brain vault and commit (dev machine only)."""
    if not BRAIN_DIR.exists():
        log.warning("[brain] Local BRAIN_DIR not found (%s) — skipping local commit.", BRAIN_DIR)
        return

    DAILY_DIR.mkdir(parents=True, exist_ok=True)
    target = DAILY_DIR / f"{run_date}.md"

    if target.exists():
        existing = target.read_text(encoding="utf-8")
        if existing.strip() == content.strip():
            log.info("[brain] Local file unchanged — skipping commit.")
            return

    target.write_text(content, encoding="utf-8")

    subprocess.run(["git", "add", str(target)], cwd=BRAIN_DIR, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", f"briefing: daily briefing {run_date}"],
        cwd=BRAIN_DIR, check=True, capture_output=True,
    )
    log.info("[brain] Local commit: %s", target)


def github_read(path: str) -> str | None:
    """Read a file from GitHub. Returns decoded text, None on 404 or missing token."""
    cfg = _gh_config()
    if not cfg:
        log.warning("[brain] GITHUB_TOKEN not set — skipping github_read.")
        return None
    token, owner, repo = cfg
    api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    try:
        resp = requests.get(api_url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return base64.b64decode(data["content"].replace("\n", "")).decode("utf-8")
        if resp.status_code != 404:
            log.warning("[brain] github_read HTTP %s for %s", resp.status_code, path)
        return None
    except requests.RequestException as e:
        log.warning("[brain] github_read failed: %s", e)
        return None


def github_read_modify_write(
    path: str,
    mutate_fn: Callable[[str], str],
    commit_msg: str,
) -> None:
    """Read path from GitHub, apply mutate_fn(current_text) → new_text, write back.

    Creates the file if it doesn't exist (mutate_fn receives "" in that case).
    Raises RuntimeError on GitHub API failure so callers can report the error.
    """
    cfg = _gh_config()
    if not cfg:
        raise RuntimeError("GITHUB_TOKEN not set — cannot write to brain.")
    token, owner, repo = cfg

    api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    sha: str | None = None
    current_text = ""
    try:
        resp = requests.get(api_url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            sha = data.get("sha")
            current_text = base64.b64decode(
                data["content"].replace("\n", "")
            ).decode("utf-8")
        elif resp.status_code != 404:
            raise RuntimeError(f"GitHub GET failed: HTTP {resp.status_code}")
    except requests.RequestException as e:
        raise RuntimeError(f"GitHub GET request failed: {e}") from e

    new_text = mutate_fn(current_text)

    body: dict = {
        "message": commit_msg,
        "content": base64.b64encode(new_text.encode("utf-8")).decode("ascii"),
        "branch": "main",
    }
    if sha:
        body["sha"] = sha

    try:
        resp = requests.put(api_url, headers=headers, json=body, timeout=30)
    except requests.RequestException as e:
        raise RuntimeError(f"GitHub PUT request failed: {e}") from e

    if resp.status_code not in (200, 201):
        raise RuntimeError(
            f"GitHub PUT failed: HTTP {resp.status_code} — {resp.text[:200]}"
        )
    action = "updated" if sha else "created"
    log.info("[brain] github_read_modify_write OK — %s %s", action, path)


def sync(run_date: str, content: str) -> None:
    """
    Push briefing to GitHub (if token available) and commit locally (if path exists).
    Logs warnings on failure — never raises.
    """
    cfg = _gh_config()
    if cfg:
        token, owner, repo = cfg
        _github_put(token, owner, repo, run_date, content)
    else:
        log.warning("[brain] GITHUB_TOKEN not set — skipping GitHub push.")

    try:
        _local_commit(run_date, content)
    except subprocess.CalledProcessError as e:
        log.warning("[brain] Local commit failed (non-fatal): %s", e.stderr or e)
    except Exception as e:
        log.warning("[brain] Local sync error (non-fatal): %s", e)


if __name__ == "__main__":
    import sys
    date = sys.argv[1] if len(sys.argv) > 1 else "2026-04-26"
    sync(date, f"# Test briefing {date}\n\nTest content from sync_to_brain.py smoke test.")
    print("Sync complete.")
