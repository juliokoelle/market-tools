"""Tests for capture_router. Mocks all external calls."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock, call
from scripts.classifier import CapturedItem


@pytest.mark.asyncio
async def test_route_task_writes_to_obsidian():
    item = CapturedItem(type="task", text="Call dentist", metadata={})
    with patch("scripts.capture_router.github_read_modify_write") as mock_gh:
        from scripts.capture_router import route_item
        await route_item(item)
    mock_gh.assert_called_once()
    path, mutate_fn, commit_msg = mock_gh.call_args[0]
    assert path.startswith("10_Daily/")
    mutated = mutate_fn("# Date\n\n## Tasks\n\n## Notes\n")
    assert "- [ ] Call dentist" in mutated


@pytest.mark.asyncio
async def test_route_question_writes_to_open_questions():
    item = CapturedItem(type="question", text="How does DCF work?", metadata={})
    with patch("scripts.capture_router.github_read_modify_write") as mock_gh:
        from scripts.capture_router import route_item
        await route_item(item)
    path = mock_gh.call_args[0][0]
    assert path == "40_Knowledge/open-questions.md"


@pytest.mark.asyncio
async def test_route_idea_adds_lightbulb_prefix():
    item = CapturedItem(type="idea", text="Build a habit tracker", metadata={})
    with patch("scripts.capture_router.github_read_modify_write") as mock_gh:
        from scripts.capture_router import route_item
        await route_item(item)
    path, mutate_fn, _ = mock_gh.call_args[0]
    mutated = mutate_fn("# Date\n\n## Notes\n\n## Focus\n")
    assert "💡" in mutated
    assert "Build a habit tracker" in mutated


@pytest.mark.asyncio
async def test_route_gift_idea_uses_person_filename():
    item = CapturedItem(type="gift_idea", text="Buch für Mama", metadata={"person": "Mama", "item": "Buch"})
    with patch("scripts.capture_router.github_read_modify_write") as mock_gh:
        from scripts.capture_router import route_item
        await route_item(item)
    path = mock_gh.call_args[0][0]
    assert path == "50_People/mama.md"


@pytest.mark.asyncio
async def test_route_gift_idea_creates_new_person_file():
    item = CapturedItem(type="gift_idea", text="Wein für Klaus Müller", metadata={"person": "Klaus Müller", "item": "Wein"})
    with patch("scripts.capture_router.github_read_modify_write") as mock_gh:
        from scripts.capture_router import route_item
        await route_item(item)
    path, mutate_fn, _ = mock_gh.call_args[0]
    assert path == "50_People/klaus-müller.md"
    created = mutate_fn("")  # empty = new file
    assert "## Geschenkideen" in created
    assert "Wein" in created


@pytest.mark.asyncio
async def test_route_wishlist_calls_both_obsidian_and_api():
    item = CapturedItem(
        type="wishlist", text="Arc'teryx Jacke",
        metadata={"name": "Arc'teryx Jacke", "brand": "Arc'teryx", "price": None}
    )
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    with patch("scripts.capture_router.github_read_modify_write") as mock_gh, \
         patch("scripts.capture_router.httpx.AsyncClient") as MockHttp:
        MockHttp.return_value.__aenter__ = AsyncMock(return_value=MockHttp.return_value)
        MockHttp.return_value.__aexit__ = AsyncMock(return_value=False)
        MockHttp.return_value.post = AsyncMock(return_value=mock_resp)
        from scripts.capture_router import route_item
        await route_item(item)
    mock_gh.assert_called_once()
    MockHttp.return_value.post.assert_called_once()
    call_args = MockHttp.return_value.post.call_args
    payload = call_args[1]["json"]
    assert payload["name"] == "Arc'teryx Jacke"
    assert payload["brand"] == "Arc'teryx"
    assert payload["priority"] == 2


@pytest.mark.asyncio
async def test_route_stock_pick_writes_obsidian_and_posts_to_market_tools():
    item = CapturedItem(type="stock_pick", text="ASML interessant", metadata={"ticker": "ASML", "notes": "AI play"})
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    with patch("scripts.capture_router.github_read_modify_write") as mock_gh, \
         patch("scripts.capture_router.httpx.AsyncClient") as MockHttp:
        MockHttp.return_value.__aenter__ = AsyncMock(return_value=MockHttp.return_value)
        MockHttp.return_value.__aexit__ = AsyncMock(return_value=False)
        MockHttp.return_value.post = AsyncMock(return_value=mock_resp)
        from scripts.capture_router import route_item
        await route_item(item)
    path, mutate_fn, _ = mock_gh.call_args[0]
    mutated = mutate_fn("# Date\n\n## Notes\n\n## Focus\n")
    assert "$ASML" in mutated
    assert "AI play" in mutated
    call_args = MockHttp.return_value.post.call_args
    assert "stock-watchlist" in call_args[0][0]
    assert call_args[1]["json"]["ticker"] == "ASML"


@pytest.mark.asyncio
async def test_route_item_never_raises_on_github_failure():
    item = CapturedItem(type="task", text="Something", metadata={})
    with patch("scripts.capture_router.github_read_modify_write", side_effect=Exception("network error")):
        from scripts.capture_router import route_item
        await route_item(item)  # must not raise


@pytest.mark.asyncio
async def test_route_reminder_writes_to_followups():
    item = CapturedItem(type="reminder", text="Arzttermin", metadata={"text": "Arzttermin", "date": "Montag"})
    with patch("scripts.capture_router.github_read_modify_write") as mock_gh:
        from scripts.capture_router import route_item
        await route_item(item)
    path, mutate_fn, _ = mock_gh.call_args[0]
    mutated = mutate_fn("# Date\n\n## Follow-ups\n\n## Focus\n")
    assert "Arzttermin" in mutated
    assert "Montag" in mutated
