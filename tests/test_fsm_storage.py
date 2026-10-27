"""Persistent SQLite FSM storage + resume-after-restart."""

from __future__ import annotations

from pathlib import Path

import pytest

from aiogram.fsm.storage.base import StorageKey
from bot.fsm_storage import SQLiteStorage
from bot.states import BookingFSM


def _key(user_id: int = 42, chat_id: int = 42, bot_id: int = 1) -> StorageKey:
    return StorageKey(bot_id=bot_id, chat_id=chat_id, user_id=user_id)


@pytest.mark.asyncio
async def test_set_get_state_and_data(tmp_path: Path) -> None:
    path = tmp_path / "fsm.db"
    storage = SQLiteStorage(path)
    key = _key()

    await storage.set_state(key, BookingFSM.choosing_time)
    assert await storage.get_state(key) == BookingFSM.choosing_time.state

    payload = {
        "service_id": "haircut",
        "service_name": "Стрижка",
        "duration_minutes": 45,
        "day_iso": "2026-10-28",
        "price": "400 грн",
    }
    await storage.set_data(key, payload)
    assert await storage.get_data(key) == payload

    await storage.update_data(key, {"time_hhmm": "12:00"})
    data = await storage.get_data(key)
    assert data["time_hhmm"] == "12:00"
    assert data["service_id"] == "haircut"

    await storage.close()


@pytest.mark.asyncio
async def test_resume_after_restart(tmp_path: Path) -> None:
    """Half-finished booking must survive closing the storage (simulates process restart)."""
    path = tmp_path / "fsm.db"
    key = _key(user_id=123456789)

    first = SQLiteStorage(path)
    await first.set_state(key, BookingFSM.entering_name)
    await first.set_data(
        key,
        {
            "service_id": "manicure",
            "service_name": "Манікюр",
            "duration_minutes": 60,
            "day_iso": "2026-10-28",
            "time_hhmm": "14:30",
            "price": "450 грн",
        },
    )
    await first.close()

    second = SQLiteStorage(path)
    assert await second.get_state(key) == BookingFSM.entering_name.state
    data = await second.get_data(key)
    assert data["service_id"] == "manicure"
    assert data["time_hhmm"] == "14:30"
    assert data["day_iso"] == "2026-10-28"
    await second.close()


@pytest.mark.asyncio
async def test_clear_state(tmp_path: Path) -> None:
    path = tmp_path / "fsm.db"
    storage = SQLiteStorage(path)
    key = _key(user_id=7)
    await storage.set_state(key, BookingFSM.confirming)
    await storage.set_data(key, {"client_name": "Аня"})
    await storage.set_state(key, None)
    await storage.set_data(key, {})
    assert await storage.get_state(key) is None
    assert await storage.get_data(key) == {}
    await storage.close()


@pytest.mark.asyncio
async def test_independent_keys(tmp_path: Path) -> None:
    path = tmp_path / "fsm.db"
    storage = SQLiteStorage(path)
    a = _key(user_id=1)
    b = _key(user_id=2)
    await storage.set_state(a, BookingFSM.choosing_service)
    await storage.set_state(b, BookingFSM.choosing_date)
    assert await storage.get_state(a) == BookingFSM.choosing_service.state
    assert await storage.get_state(b) == BookingFSM.choosing_date.state
    await storage.close()
