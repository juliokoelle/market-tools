"""Unit tests for price conversion and formatting utilities."""

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
