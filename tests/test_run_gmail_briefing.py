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
    monkeypatch.setattr(runner, "fetch_today_briefing", lambda target_date=None: None)
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
    monkeypatch.setattr(runner, "fetch_today_briefing", lambda target_date=None: "## MarketsXrunch\n\nGold +1%.")
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
    monkeypatch.setattr(runner, "fetch_today_briefing", lambda target_date=None: "## Section\n\nContent.")
    monkeypatch.setattr(runner, "brain_sync",
                        lambda d, c: (_ for _ in ()).throw(RuntimeError("sync failed")))
    monkeypatch.setattr(runner, "today",                lambda: "2026-05-08")
    runner.run()  # must not raise
    assert (tmp_path / "latest-briefing.md").exists()
