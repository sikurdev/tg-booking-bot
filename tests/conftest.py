from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
import pytest_asyncio

from bot.config import BusinessConfig, DayHours, Service, load_business_config
from bot.db import Database

TZ = "Europe/Kyiv"
TZINFO = ZoneInfo(TZ)


@pytest.fixture
def demo_config_path() -> Path:
    return Path(__file__).resolve().parents[1] / "config" / "demo_salon.yaml"


@pytest.fixture
def biz(demo_config_path: Path) -> BusinessConfig:
    return load_business_config(demo_config_path, timezone=TZ)


@pytest.fixture
def simple_biz() -> BusinessConfig:
    return BusinessConfig(
        name="Test",
        address="Addr",
        phone="+380",
        language="uk",
        slot_step_minutes=30,
        booking_horizon_days=7,
        working_hours={
            0: DayHours("09:00", "12:00"),  # Monday
            1: DayHours("09:00", "17:00"),
        },
        days_off=["2026-11-03"],  # a Tuesday that would otherwise be open
        services=[
            Service("cut", "Cut", 60, "Ціна за запитом"),
            Service("quick", "Quick", 30, 100),
        ],
        timezone=TZ,
    )


@pytest_asyncio.fixture
async def db(tmp_path: Path) -> Database:
    path = tmp_path / "test.db"
    database = Database(path, timezone=TZ)
    await database.init()
    return database


def dt(day: str, hhmm: str) -> datetime:
    return datetime.fromisoformat(f"{day}T{hhmm}:00").replace(tzinfo=TZINFO)
