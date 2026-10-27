"""Owner / demo notification deduplication."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from zoneinfo import ZoneInfo

import pytest

from bot.config import load_business_config, AppSettings
from bot.db import Booking
from bot.notify import (
    client_confirmation_text,
    is_owner_booking,
    notify_owner_new,
)


TZ = ZoneInfo("Europe/Kyiv")
OWNER_ID = 111111111
OTHER_ID = 222222222


def _settings(*, demo: bool) -> AppSettings:
    biz = load_business_config(
        Path(__file__).resolve().parents[1] / "config" / "demo_salon.yaml",
        timezone="Europe/Kyiv",
    )
    return AppSettings(
        bot_token="TEST:token",
        owner_chat_id=OWNER_ID,
        business_config_path=Path("config/demo_salon.yaml"),
        database_path=Path("data/bookings.db"),
        demo=demo,
        timezone="Europe/Kyiv",
        business=biz,
    )


def _booking(user_id: int) -> Booking:
    starts = datetime(2026, 10, 28, 12, 0, tzinfo=TZ)
    ends = datetime(2026, 10, 28, 12, 45, tzinfo=TZ)
    return Booking(
        id=1,
        user_id=user_id,
        client_name="Тест",
        phone="+380501234567",
        service_id="haircut",
        service_name="Стрижка",
        duration_minutes=45,
        starts_at=starts,
        ends_at=ends,
        status="active",
        created_at=starts,
    )


def test_owner_confirmation_is_single_combined_message() -> None:
    settings = _settings(demo=True)
    booking = _booking(OWNER_ID)
    assert is_owner_booking(settings, booking)
    text = client_confirmation_text(settings, booking)
    assert "Запис створено" in text
    assert "Новий запис" in text
    # Must NOT nest a separate [ДЕМО] copy — one message only.
    assert "[ДЕМО]" not in text
    # Exactly one confirmation block + one owner block
    assert text.count("Запис створено") == 1
    assert text.count("Новий запис") == 1


@pytest.mark.asyncio
async def test_owner_booking_sends_no_extra_notify() -> None:
    settings = _settings(demo=True)
    booking = _booking(OWNER_ID)
    bot = MagicMock()
    bot.send_message = AsyncMock()
    await notify_owner_new(bot, settings, booking)
    bot.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_non_owner_demo_gets_owner_plus_demo_copy() -> None:
    settings = _settings(demo=True)
    booking = _booking(OTHER_ID)
    bot = MagicMock()
    bot.send_message = AsyncMock()
    await notify_owner_new(bot, settings, booking)
    assert bot.send_message.await_count == 2
    owner_call = bot.send_message.await_args_list[0]
    demo_call = bot.send_message.await_args_list[1]
    assert owner_call.args[0] == OWNER_ID
    assert "Новий запис" in owner_call.args[1]
    assert demo_call.args[0] == OTHER_ID
    assert "[ДЕМО]" in demo_call.args[1]


@pytest.mark.asyncio
async def test_non_owner_non_demo_only_owner_message() -> None:
    settings = _settings(demo=False)
    booking = _booking(OTHER_ID)
    bot = MagicMock()
    bot.send_message = AsyncMock()
    await notify_owner_new(bot, settings, booking)
    assert bot.send_message.await_count == 1
    assert bot.send_message.await_args.args[0] == OWNER_ID


def test_non_owner_confirmation_is_plain_booked_ok() -> None:
    settings = _settings(demo=True)
    booking = _booking(OTHER_ID)
    text = client_confirmation_text(settings, booking)
    assert "Запис створено" in text
    assert "Новий запис" not in text
