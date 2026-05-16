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
