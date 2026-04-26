"""
Save a session recap to julio-brain.

Tries GitHub Contents API first (requires GITHUB_TOKEN env var).
Falls back to local git commit + push (works on dev machine via Keychain).

Usage:
    python scripts/save_session_recap.py \
        --project market-tools \
        --slug 2026-04-26-github-storage \
        --file /tmp/session-recap.md
"""

from __future__ import annotations

import argparse
import base64
import os
import subprocess
import sys
from pathlib import Path

import requests


def _github_put(token: str, owner: str, repo: str, rel_path: str, content: str, message: str) -> bool:
    api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{rel_path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    sha = None
    try:
        r = requests.get(api_url, headers=headers, timeout=10)
        if r.status_code == 200:
            sha = r.json().get("sha")
    except requests.RequestException:
        pass

    body: dict = {
        "message": message,
        "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
        "branch": "main",
    }
    if sha:
        body["sha"] = sha

    r = requests.put(api_url, headers=headers, json=body, timeout=30)
    return r.status_code in (200, 201)


def _local_git_save(brain_dir: Path, rel_path: str, content: str, message: str) -> None:
    full_path = brain_dir / rel_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(content, encoding="utf-8")
    subprocess.run(["git", "add", str(full_path)], cwd=brain_dir, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", message], cwd=brain_dir, check=True, capture_output=True)
    subprocess.run(["git", "push"], cwd=brain_dir, check=True, capture_output=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Save session recap to julio-brain")
    parser.add_argument("--project", required=True, help="Project slug, e.g. market-tools")
    parser.add_argument("--slug", required=True, help="YYYY-MM-DD-topic slug")
    parser.add_argument("--file", required=True, help="Path to temp file containing recap markdown")
    args = parser.parse_args()

    content_path = Path(args.file)
    if not content_path.exists():
        print(f"ERROR: content file not found: {args.file}", file=sys.stderr)
        sys.exit(1)

    content = content_path.read_text(encoding="utf-8")
    rel_path = f"30_Projects/{args.project}/sessions/{args.slug}.md"
    commit_msg = f"session-recap: {args.slug}"

    token = os.getenv("GITHUB_TOKEN", "").strip()
    owner = os.getenv("JULIO_BRAIN_OWNER", "juliokoelle")
    repo  = os.getenv("JULIO_BRAIN_REPO_NAME", "julio-brain")

    if token:
        ok = _github_put(token, owner, repo, rel_path, content, commit_msg)
        if ok:
            print(f"Session-Recap saved to 30_Projects/{args.project}/sessions/{args.slug}.md")
            sys.exit(0)
        print("GitHub API push failed — falling back to local git.", file=sys.stderr)

    brain_dir = Path.home() / "projects" / "julio-brain"
    if not brain_dir.exists():
        print(f"ERROR: GITHUB_TOKEN not set and local brain dir not found: {brain_dir}", file=sys.stderr)
        sys.exit(1)

    try:
        _local_git_save(brain_dir, rel_path, content, commit_msg)
        print(f"Session-Recap saved (local git) to 30_Projects/{args.project}/sessions/{args.slug}.md")
    except subprocess.CalledProcessError as e:
        print(f"ERROR: local git failed: {e.stderr or e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
