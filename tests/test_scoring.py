"""Unit tests for scripts/scoring.py — pure functions only, no network calls."""

import pytest
from scripts.scoring import (
    _clamp,
    _return_to_score,
    _pe_to_score,
    _pb_to_score,
    _keyword_sentiment,
    _is_crypto,
    _SENTIMENT_SCORE_MAP,
)


class TestClamp:
    def test_within_range(self):
        assert _clamp(50.0) == 50.0

    def test_below_minimum(self):
        assert _clamp(-10.0) == 0.0

    def test_above_maximum(self):
        assert _clamp(150.0) == 100.0

    def test_at_boundary(self):
        assert _clamp(0.0) == 0.0
        assert _clamp(100.0) == 100.0


class TestReturnToScore:
    def test_zero_return_is_midpoint(self):
        assert _return_to_score(0.0) == 50.0

    def test_positive_return_above_midpoint(self):
        assert _return_to_score(0.10) > 50.0

    def test_negative_return_below_midpoint(self):
        assert _return_to_score(-0.10) < 50.0

    def test_none_is_midpoint(self):
        assert _return_to_score(None) == 50.0

    def test_large_positive_clamped_to_100(self):
        assert _return_to_score(1.0) == 100.0

    def test_large_negative_clamped_to_0(self):
        assert _return_to_score(-1.0) == 0.0

    def test_scale_parameter(self):
        # With scale=0.10, a +10% return should yield 100
        assert _return_to_score(0.10, scale=0.10) == 100.0


class TestPeToScore:
    def test_low_pe_high_score(self):
        assert _pe_to_score(8.0) == 90.0

    def test_mid_pe_mid_score(self):
        assert _pe_to_score(22.0) == 60.0

    def test_high_pe_low_score(self):
        assert _pe_to_score(60.0) == 20.0

    def test_boundary_values(self):
        assert _pe_to_score(10.0) == 80.0
        assert _pe_to_score(15.0) == 70.0
        assert _pe_to_score(20.0) == 60.0
        assert _pe_to_score(25.0) == 50.0
        assert _pe_to_score(35.0) == 35.0
        assert _pe_to_score(50.0) == 20.0


class TestPbToScore:
    def test_low_pb_high_score(self):
        assert _pb_to_score(0.8) == 85.0

    def test_high_pb_low_score(self):
        assert _pb_to_score(10.0) == 20.0

    def test_boundary_values(self):
        assert _pb_to_score(1.0) == 70.0
        assert _pb_to_score(2.0) == 55.0
        assert _pb_to_score(4.0) == 35.0
        assert _pb_to_score(8.0) == 20.0


class TestKeywordSentiment:
    def test_positive_headlines(self):
        headlines = ["Apple surges on record revenue beat", "Strong growth outlook"]
        label, score = _keyword_sentiment(headlines)
        assert label == "bullish"
        assert score == _SENTIMENT_SCORE_MAP["bullish"]

    def test_negative_headlines(self):
        headlines = ["Stock drops on earnings miss", "Layoffs cut jobs amid weak demand"]
        label, score = _keyword_sentiment(headlines)
        assert label == "bearish"
        assert score == _SENTIMENT_SCORE_MAP["bearish"]

    def test_neutral_headlines(self):
        headlines = ["Company announces new product line"]
        label, score = _keyword_sentiment(headlines)
        assert label == "neutral"
        assert score == _SENTIMENT_SCORE_MAP["neutral"]

    def test_empty_headlines_neutral(self):
        label, score = _keyword_sentiment([])
        assert label == "neutral"

    def test_tie_is_neutral(self):
        # "surge" matches POSITIVE_KW, "fall" matches NEGATIVE_KW → equal → neutral
        headlines = ["surge and fall"]
        label, score = _keyword_sentiment(headlines)
        assert label == "neutral"


class TestIsCrypto:
    def test_btc_is_crypto(self):
        assert _is_crypto("BTC-USD") is True

    def test_eth_is_crypto(self):
        assert _is_crypto("ETH-USD") is True

    def test_aapl_is_not_crypto(self):
        assert _is_crypto("AAPL") is False

    def test_nvda_is_not_crypto(self):
        assert _is_crypto("NVDA") is False

    def test_case_insensitive(self):
        assert _is_crypto("btc-usd") is True

    def test_european_ticker_is_not_crypto(self):
        assert _is_crypto("ASM.AS") is False
        assert _is_crypto("MC.PA") is False
