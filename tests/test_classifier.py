"""Tests for the LLM classifier. All tests mock the Anthropic client."""
import os
from unittest.mock import MagicMock, patch


def _mock_anthropic_response(json_str: str):
    msg = MagicMock()
    msg.content = [MagicMock(text=json_str)]
    return msg


def test_classify_wishlist_item(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "dummy-key")
    with patch("scripts.classifier.anthropic.Anthropic") as MockClient:
        MockClient.return_value.messages.create.return_value = _mock_anthropic_response(
            '[{"type": "wishlist", "text": "Arc\'teryx Jacke", '
            '"metadata": {"name": "Arc\'teryx Jacke", "brand": "Arc\'teryx", "price": null}}]'
        )
        from scripts.classifier import classify_text
        items = classify_text("ich will eine Arc'teryx Jacke kaufen")
    assert len(items) == 1
    assert items[0].type == "wishlist"
    assert items[0].metadata["name"] == "Arc'teryx Jacke"
    assert items[0].metadata["brand"] == "Arc'teryx"


def test_classify_stock_pick(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "dummy-key")
    with patch("scripts.classifier.anthropic.Anthropic") as MockClient:
        MockClient.return_value.messages.create.return_value = _mock_anthropic_response(
            '[{"type": "stock_pick", "text": "ASML interessant", '
            '"metadata": {"ticker": "ASML", "notes": "interessant"}}]'
        )
        from scripts.classifier import classify_text
        items = classify_text("ASML finde ich gerade sehr interessant")
    assert items[0].type == "stock_pick"
    assert items[0].metadata["ticker"] == "ASML"


def test_classify_multi_item_voice_note(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "dummy-key")
    with patch("scripts.classifier.anthropic.Anthropic") as MockClient:
        MockClient.return_value.messages.create.return_value = _mock_anthropic_response(
            '[{"type": "wishlist", "text": "Fahrradhelm", "metadata": {"name": "Fahrradhelm", "brand": null, "price": null}}, '
            '{"type": "stock_pick", "text": "ASML anschauen", "metadata": {"ticker": "ASML", "notes": null}}]'
        )
        from scripts.classifier import classify_text
        items = classify_text("ich brauche einen Fahrradhelm und ASML ist interessant")
    assert len(items) == 2
    assert items[0].type == "wishlist"
    assert items[1].type == "stock_pick"


def test_classify_gift_idea(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "dummy-key")
    with patch("scripts.classifier.anthropic.Anthropic") as MockClient:
        MockClient.return_value.messages.create.return_value = _mock_anthropic_response(
            '[{"type": "gift_idea", "text": "Buch für Mama", '
            '"metadata": {"person": "Mama", "item": "Buch"}}]'
        )
        from scripts.classifier import classify_text
        items = classify_text("für Mama wäre ein Buch schön")
    assert items[0].type == "gift_idea"
    assert items[0].metadata["person"] == "Mama"
    assert items[0].metadata["item"] == "Buch"


def test_classify_falls_back_to_note_on_invalid_json(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "dummy-key")
    with patch("scripts.classifier.anthropic.Anthropic") as MockClient:
        MockClient.return_value.messages.create.return_value = _mock_anthropic_response(
            "not valid json at all"
        )
        from scripts.classifier import classify_text
        items = classify_text("some input")
    assert len(items) == 1
    assert items[0].type == "note"
    assert items[0].text == "some input"


def test_classify_falls_back_on_unknown_type(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "dummy-key")
    with patch("scripts.classifier.anthropic.Anthropic") as MockClient:
        MockClient.return_value.messages.create.return_value = _mock_anthropic_response(
            '[{"type": "invented_type", "text": "foo", "metadata": {}}]'
        )
        from scripts.classifier import classify_text
        items = classify_text("foo")
    assert items[0].type == "note"


def test_classify_falls_back_when_no_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    import importlib, scripts.classifier as m
    importlib.reload(m)
    items = m.classify_text("test text")
    assert len(items) == 1
    assert items[0].type == "note"
    assert items[0].text == "test text"


def test_classify_never_returns_empty_array(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "dummy-key")
    with patch("scripts.classifier.anthropic.Anthropic") as MockClient:
        MockClient.return_value.messages.create.return_value = _mock_anthropic_response("[]")
        from scripts.classifier import classify_text
        items = classify_text("something")
    assert len(items) >= 1


def test_classify_code_fence_json_still_parsed(monkeypatch):
    """Haiku sometimes returns ```json ... ``` — must not fall back to note."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "dummy-key")
    with patch("scripts.classifier.anthropic.Anthropic") as MockClient:
        MockClient.return_value.messages.create.return_value = _mock_anthropic_response(
            '```json\n[{"type": "stock_pick", "text": "NVDA", '
            '"metadata": {"ticker": "NVDA", "company": "NVIDIA", "notes": null}}]\n```'
        )
        from scripts.classifier import classify_text
        items = classify_text("NVDA auf Watchlist")
    assert items[0].type == "stock_pick"
    assert items[0].metadata["ticker"] == "NVDA"


def test_classify_stock_by_company_name(monkeypatch):
    """Company names like 'monday.com' should resolve to their ticker."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "dummy-key")
    with patch("scripts.classifier.anthropic.Anthropic") as MockClient:
        MockClient.return_value.messages.create.return_value = _mock_anthropic_response(
            '[{"type": "stock_pick", "text": "monday.com", '
            '"metadata": {"ticker": "MNDY", "company": "monday.com", "notes": null}}]'
        )
        from scripts.classifier import classify_text
        items = classify_text("monday.com beobachten")
    assert items[0].type == "stock_pick"
    assert items[0].metadata["ticker"] == "MNDY"


def test_classify_multiple_stocks(monkeypatch):
    """A message with 4 stocks should produce 4 stock_pick items."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "dummy-key")
    payload = '[{"type":"stock_pick","text":"monday.com","metadata":{"ticker":"MNDY","company":"monday.com","notes":null}},' \
              '{"type":"stock_pick","text":"take-two","metadata":{"ticker":"TTWO","company":"Take-Two Interactive","notes":null}},' \
              '{"type":"stock_pick","text":"Hims","metadata":{"ticker":"HIMS","company":"Hims & Hers","notes":null}},' \
              '{"type":"stock_pick","text":"Shopify","metadata":{"ticker":"SHOP","company":"Shopify","notes":null}}]'
    with patch("scripts.classifier.anthropic.Anthropic") as MockClient:
        MockClient.return_value.messages.create.return_value = _mock_anthropic_response(payload)
        from scripts.classifier import classify_text
        items = classify_text("Aktien: monday.com, take-two, Hims, Shopify")
    assert len(items) == 4
    assert all(i.type == "stock_pick" for i in items)
    tickers = {i.metadata["ticker"] for i in items}
    assert tickers == {"MNDY", "TTWO", "HIMS", "SHOP"}


def test_classify_reminder(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "dummy-key")
    with patch("scripts.classifier.anthropic.Anthropic") as MockClient:
        MockClient.return_value.messages.create.return_value = _mock_anthropic_response(
            '[{"type": "reminder", "text": "Zahnarzt anrufen", '
            '"metadata": {"text": "Zahnarzt anrufen", "date": "2026-06-01"}}]'
        )
        from scripts.classifier import classify_text
        items = classify_text("Morgen Zahnarzt anrufen nicht vergessen")
    assert items[0].type == "reminder"
    assert items[0].metadata["date"] == "2026-06-01"


def test_classify_task(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "dummy-key")
    with patch("scripts.classifier.anthropic.Anthropic") as MockClient:
        MockClient.return_value.messages.create.return_value = _mock_anthropic_response(
            '[{"type": "task", "text": "PR review abschließen", "metadata": {}}]'
        )
        from scripts.classifier import classify_text
        items = classify_text("muss noch PR review abschließen")
    assert items[0].type == "task"
