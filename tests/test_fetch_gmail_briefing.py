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
