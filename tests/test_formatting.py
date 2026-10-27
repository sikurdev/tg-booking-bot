"""Hours collapse + human date/time formatting."""

from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from bot.config import BusinessConfig, DayHours, Service
from bot.formatting import (
    EN_DASH,
    format_day_human,
    format_day_short,
    format_when,
    format_when_parts,
    format_working_hours_block,
    format_working_hours_lines,
)


def _biz(hours: dict[int, DayHours | None], lang: str = "uk") -> BusinessConfig:
    wh = {d: h for d, h in hours.items() if h is not None}
    return BusinessConfig(
        name="Test",
        address="Addr",
        phone="+380",
        language=lang,
        slot_step_minutes=30,
        booking_horizon_days=7,
        working_hours=wh,
        days_off=[],
        services=[Service("cut", "Cut", 60, 100)],
        timezone="Europe/Kyiv",
    )


def test_collapse_mon_fri_same_hours(biz):
    lines = format_working_hours_lines(biz)
    assert lines[0].startswith(f"Пн{EN_DASH}Пт")
    assert "10:00" + EN_DASH + "19:00" in lines[0]
    assert lines[1].startswith("Сб")
    assert "10:00" + EN_DASH + "16:00" in lines[1]
    assert lines[2].startswith("Нд")
    assert "вихідний" in lines[2]
    assert "—" not in "\n".join(lines)
    # Hours column aligns across rows
    cols = [line.index("10:00") if "10:00" in line else line.index("вихідний") for line in lines]
    assert len(set(cols)) == 1


def test_hours_block_is_html_pre(biz):
    block = format_working_hours_block(biz)
    assert block.startswith("🕒 <b>Графік роботи</b>")
    assert "<pre>" in block and "</pre>" in block
    assert "вихідний" in block
    assert EN_DASH in block


def test_no_collapse_when_hours_differ():
    biz = _biz(
        {
            0: DayHours("10:00", "19:00"),
            1: DayHours("11:00", "19:00"),
            2: DayHours("10:00", "19:00"),
            3: None,
            4: None,
            5: DayHours("10:00", "16:00"),
            6: None,
        }
    )
    lines = format_working_hours_lines(biz)
    joined = "\n".join(lines)
    assert "Пн  " in joined or joined.split("\n")[0].startswith("Пн")
    assert any(line.startswith("Вт") for line in lines)
    # Thu–Sun off collapse? Thu+Fri off consecutive, Sat open, Sun off
    assert any(f"Чт{EN_DASH}Пт" in line or line.startswith("Чт") for line in lines)
    assert sum("вихідний" in line for line in lines) >= 2


def test_all_same_hours_one_line():
    same = DayHours("09:00", "18:00")
    biz = _biz({d: same for d in range(7)})
    lines = format_working_hours_lines(biz)
    assert len(lines) == 1
    assert lines[0].startswith(f"Пн{EN_DASH}Нд")


def test_format_when_uk():
    # 2026-10-28 is Wednesday
    dt = datetime(2026, 10, 28, 12, 0, tzinfo=ZoneInfo("Europe/Kyiv"))
    assert format_when(dt, "uk") == "Ср, 28 жовтня · 12:00"
    assert format_day_human(date(2026, 10, 28), "uk") == "Ср, 28 жовтня"
    assert format_day_short(date(2026, 10, 28), "uk") == "Ср, 28 жовт."
    assert format_when_parts(date(2026, 10, 28), "12:00", "uk") == "Ср, 28 жовтня · 12:00"


def test_format_when_ru():
    dt = datetime(2026, 10, 28, 12, 0, tzinfo=ZoneInfo("Europe/Kyiv"))
    assert format_when(dt, "ru") == "Ср, 28 октября · 12:00"


def test_welcome_has_no_commands_and_uses_hours_block(biz):
    from pathlib import Path

    from bot.config import AppSettings
    from bot.handlers.common import contacts_text, welcome_text

    settings = AppSettings(
        bot_token="x",
        owner_chat_id=1,
        business_config_path=Path("config/demo_salon.yaml"),
        database_path=Path("data/bookings.db"),
        demo=True,
        timezone="Europe/Kyiv",
        business=biz,
    )
    text = welcome_text(settings)
    assert "<b>" in text
    assert biz.name in text
    assert "/my" not in text
    assert "/admin" not in text
    assert "/start" not in text
    assert "<pre>" in text
    assert "вихідний" in text
    # Old long hours line must not appear
    assert "Пн: " not in text
    assert "Вт: " not in text
    assert " · " not in text.split("<pre>")[-1]  # no ·-joined hours inside pre

    c = contacts_text(settings)
    assert "<pre>" in c
    assert "вихідний" in c
    assert "/my" not in c
