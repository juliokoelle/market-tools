"""Tests for the shared Telegram send helper and the GitHub conflict retry."""

from unittest.mock import MagicMock, patch

import pytest
import requests


# ---------------------------------------------------------------------------
# telegram_utils.send_message — plain-text fallback on Markdown parse error
# ---------------------------------------------------------------------------

def _resp(status: int, text: str = "") -> MagicMock:
    r = MagicMock()
    r.status_code = status
    r.text = text
    r.raise_for_status.side_effect = (
        requests.HTTPError(f"HTTP {status}") if status >= 400 else None
    )
    return r


def test_send_message_success_keeps_markdown():
    from scripts.telegram_utils import send_message

    with patch("scripts.telegram_utils.requests.post", return_value=_resp(200)) as post:
        send_message("TOKEN", 123, "*bold*")
    assert post.call_count == 1
    assert post.call_args.kwargs["json"]["parse_mode"] == "Markdown"


def test_send_message_retries_plain_on_400():
    from scripts.telegram_utils import send_message

    responses = [_resp(400, "can't parse entities"), _resp(200)]
    with patch("scripts.telegram_utils.requests.post", side_effect=responses) as post:
        send_message("TOKEN", 123, "broken _markdown")
    assert post.call_count == 2
    # Second (successful) attempt must drop parse_mode.
    assert "parse_mode" not in post.call_args_list[1].kwargs["json"]


def test_send_message_raises_when_plain_also_fails():
    from scripts.telegram_utils import send_message

    responses = [_resp(400), _resp(403, "forbidden")]
    with patch("scripts.telegram_utils.requests.post", side_effect=responses):
        with pytest.raises(requests.HTTPError):
            send_message("TOKEN", 123, "x")


# ---------------------------------------------------------------------------
# sync_to_brain.github_read_modify_write — 409 conflict retry
# ---------------------------------------------------------------------------

def _gh_get(sha: str, content_b64: str) -> MagicMock:
    r = MagicMock()
    r.status_code = 200
    r.json.return_value = {"sha": sha, "content": content_b64}
    return r


def test_rmw_retries_on_409_then_succeeds(monkeypatch):
    import scripts.sync_to_brain as s

    monkeypatch.setenv("GITHUB_TOKEN", "tok")
    monkeypatch.setattr(s.time, "sleep", lambda *_: None)

    import base64
    empty_b64 = base64.b64encode(b"# Note\n").decode()

    get_resp = _gh_get("sha1", empty_b64)
    put_conflict = MagicMock(status_code=409, text="conflict")
    put_ok = MagicMock(status_code=200, text="")

    with patch.object(s.requests, "get", return_value=get_resp), \
         patch.object(s.requests, "put", side_effect=[put_conflict, put_ok]) as put:
        s.github_read_modify_write("10_Daily/x.md", lambda cur: cur + "more\n", "msg")

    assert put.call_count == 2  # retried after the 409


def test_rmw_raises_after_exhausting_retries(monkeypatch):
    import scripts.sync_to_brain as s

    monkeypatch.setenv("GITHUB_TOKEN", "tok")
    monkeypatch.setattr(s.time, "sleep", lambda *_: None)

    import base64
    b64 = base64.b64encode(b"x").decode()

    with patch.object(s.requests, "get", return_value=_gh_get("sha", b64)), \
         patch.object(s.requests, "put", return_value=MagicMock(status_code=409, text="c")):
        with pytest.raises(RuntimeError, match="HTTP 409"):
            s.github_read_modify_write("p.md", lambda c: c, "m", max_attempts=3)


def test_rmw_non_conflict_error_does_not_retry(monkeypatch):
    import scripts.sync_to_brain as s

    monkeypatch.setenv("GITHUB_TOKEN", "tok")
    import base64
    b64 = base64.b64encode(b"x").decode()

    put_500 = MagicMock(status_code=500, text="server error")
    with patch.object(s.requests, "get", return_value=_gh_get("sha", b64)), \
         patch.object(s.requests, "put", return_value=put_500) as put:
        with pytest.raises(RuntimeError, match="HTTP 500"):
            s.github_read_modify_write("p.md", lambda c: c, "m")
    assert put.call_count == 1  # 500 is not a conflict — no retry
