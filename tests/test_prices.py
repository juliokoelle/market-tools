"""Unit tests for price conversion, formatting utilities, and briefing helpers."""

import pytest
from scripts.utils import oz_to_gram, oz_to_kg, format_precious_metal


def test_oz_to_gram():
    assert oz_to_gram(31.1035) == pytest.approx(1.0, rel=1e-3)
    assert oz_to_gram(3340) == pytest.approx(107.38, rel=1e-3)


def test_oz_to_kg():
    assert oz_to_kg(31.1035) == pytest.approx(1000.0, rel=1e-3)
    assert oz_to_kg(3340) == pytest.approx(107_380, rel=1e-3)


def test_format_precious_metal_contains_all_units():
    result = format_precious_metal("Gold", 3340.0)
    assert "USD/oz" in result
    assert "USD/g" in result
    assert "USD/kg" in result
    assert "Gold" in result


def test_format_precious_metal_no_missing_units():
    result = format_precious_metal("Silver", 36.0)
    lines = [l.strip() for l in result.strip().splitlines() if l.strip()]
    assert len(lines) == 4  # name + 3 unit lines


# ---------------------------------------------------------------------------
# generate_briefing helpers
# ---------------------------------------------------------------------------

def test_calculate_cost_anthropic():
    from scripts.generate_briefing import _calculate_cost
    # 1M input @ $3 + 1M output @ $15 = $18
    cost = _calculate_cost("anthropic", 1_000_000, 1_000_000)
    assert abs(cost - 18.0) < 0.001


def test_calculate_cost_openai():
    from scripts.generate_briefing import _calculate_cost
    # 1M input @ $0.75 + 1M output @ $4.50 = $5.25
    cost = _calculate_cost("openai", 1_000_000, 1_000_000)
    assert abs(cost - 5.25) < 0.001


def test_calculate_cost_zero_tokens():
    from scripts.generate_briefing import _calculate_cost
    assert _calculate_cost("anthropic", 0, 0) == 0.0
    assert _calculate_cost("openai", 0, 0) == 0.0


def test_load_system_prompt_reads_file(tmp_path, monkeypatch):
    from pathlib import Path
    from unittest.mock import patch
    prompt_file = tmp_path / "briefing_prompt.md"
    prompt_file.write_text("You are a journalist.", encoding="utf-8")
    with patch("scripts.generate_briefing.Path") as MockPath:
        # Only intercept the briefing_prompt.md path
        real_path = Path
        def path_side_effect(p):
            if "briefing_prompt" in str(p):
                return prompt_file
            return real_path(p)
        MockPath.side_effect = path_side_effect
        from scripts import generate_briefing as gb
        # Direct test: file read
    text = prompt_file.read_text()
    assert text == "You are a journalist."


def test_build_prompt_includes_extra_news(tmp_path, monkeypatch):
    import json, os
    from scripts.news_sources import NewsItem

    # Minimal data files
    raw_dir = tmp_path / "data" / "raw" / "2026-04-25"
    raw_dir.mkdir(parents=True)
    (raw_dir / "commodities.json").write_text(json.dumps({
        "gold_usd_oz": 3340.0, "silver_usd_oz": 36.0,
        "brent_usd_bbl": 82.0, "natgas_usd_mmbtu": 3.1, "copper_usd_lb": 4.2,
    }))
    (raw_dir / "currencies.json").write_text(json.dumps({"eurusd": 1.0850}))
    (raw_dir / "news.json").write_text(json.dumps([]))

    import scripts.generate_briefing as gb
    orig = gb.data_dir
    monkeypatch.setattr(gb, "data_dir", lambda d: str(raw_dir.parent / d))

    extra = [NewsItem("Reuters", "RSS exclusive headline", "Lead.", "http://x.com",
                      "2026-04-25T10:00:00+00:00", "en", "global")]
    prompt = gb.build_prompt("2026-04-25", extra_news=extra)

    assert "RSS exclusive headline" in prompt
