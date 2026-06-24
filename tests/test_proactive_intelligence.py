"""Unit tests for proactive_intelligence hint extraction + empty detection.

Pure-function tests — no network, no API calls.
"""
from scripts.proactive_intelligence import _extract_hint, _is_empty_response


class TestExtractHint:
    def test_strips_english_preamble_before_marker(self):
        raw = (
            "Looking at Julio's notes, I can see:\n\n"
            "🧠 *Second Brain Hint:* Reisepass läuft im August ab — vor Brasilien erneuern."
        )
        out = _extract_hint(raw)
        assert out.startswith("🧠")
        assert "Looking at" not in out
        assert "Reisepass" in out

    def test_marker_at_start_returned_as_is(self):
        raw = "🧠 *Second Brain Hint:* Treffen mit Paul Haltof nächste Woche."
        assert _extract_hint(raw) == raw

    def test_no_marker_returns_empty(self):
        assert _extract_hint("Here are some thoughts but no marker.") == ""

    def test_empty_input_returns_empty(self):
        assert _extract_hint("") == ""


class TestIsEmptyResponse:
    def test_empty_string(self):
        assert _is_empty_response("") is True

    def test_nichts_signal(self):
        assert _is_empty_response("NICHTS") is True

    def test_english_null_signal(self):
        assert _is_empty_response("null") is True
        assert _is_empty_response("Nothing urgent today.") is True

    def test_marker_with_label_only_is_empty(self):
        assert _is_empty_response("🧠 *Second Brain Hint:*") is True

    def test_real_hint_is_not_empty(self):
        hint = "🧠 *Second Brain Hint:* Reisepass läuft im August ab — vor Brasilien erneuern."
        assert _is_empty_response(hint) is False
