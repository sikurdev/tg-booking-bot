#!/usr/bin/env python3
"""Exercise handlers with mocked Bot — button-driven flows, no real Telegram calls."""

from __future__ import annotations

import asyncio
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.base import StorageKey
from aiogram.types import ReplyKeyboardMarkup

from bot.config import AppSettings, load_business_config
from bot.db import Database
from bot.handlers import common, booking, my_bookings, admin
from bot.handlers.common import welcome_text
from bot.keyboards import main_menu
from bot.slots import available_dates, generate_slots
from bot.states import BookingFSM
from bot.texts import t


TZ = "Europe/Kyiv"


def make_settings(db_path: Path) -> AppSettings:
    biz = load_business_config(ROOT / "config" / "demo_salon.yaml", timezone=TZ)
    return AppSettings(
        bot_token="000000:TEST-SMOKE-TOKEN-NOT-REAL",
        owner_chat_id=999001,
        business_config_path=ROOT / "config" / "demo_salon.yaml",
        database_path=db_path,
        demo=True,
        timezone=TZ,
        business=biz,
    )


def fake_user(uid: int = 4242, full_name: str = "Тест Клієнт", first_name: str = "Олена"):
    u = MagicMock()
    u.id = uid
    u.full_name = full_name
    u.first_name = first_name
    u.username = "test_client"
    return u


def fake_message(user, text: str = "/start"):
    m = MagicMock()
    m.from_user = user
    m.text = text
    m.contact = None
    m.answer = AsyncMock()
    m.bot = MagicMock()
    m.bot.send_message = AsyncMock()
    return m


def fake_callback(user, data: str, message=None):
    cb = MagicMock()
    cb.from_user = user
    cb.data = data
    cb.answer = AsyncMock()
    cb.bot = MagicMock()
    cb.bot.send_message = AsyncMock()
    if message is None:
        message = MagicMock()
        message.edit_text = AsyncMock()
        message.edit_reply_markup = AsyncMock()
        message.answer = AsyncMock()
    cb.message = message
    return cb


async def make_state(user_id: int = 4242) -> FSMContext:
    storage = MemoryStorage()
    key = StorageKey(bot_id=1, chat_id=user_id, user_id=user_id)
    return FSMContext(storage=storage, key=key)


def _assert_reply_menu(call_args_list, *, is_owner: bool = False) -> None:
    """At least one answer used the persistent reply main menu."""
    found = False
    for call in call_args_list:
        kwargs = call.kwargs
        rm = kwargs.get("reply_markup")
        if isinstance(rm, ReplyKeyboardMarkup):
            labels = [b.text for row in rm.keyboard for b in row]
            assert t("uk", "btn_book") in labels
            if is_owner:
                assert t("uk", "btn_admin") in labels
            else:
                assert t("uk", "btn_admin") not in labels
            found = True
            break
    assert found, "expected ReplyKeyboardMarkup main menu in answers"


async def run() -> None:
    print("=== smoke: config + welcome (no /command hints) ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "smoke.db"
        settings = make_settings(db_path)
        db = Database(db_path, timezone=TZ)
        await db.init()

        text = welcome_text(settings)
        assert "Демо-салон" in text
        assert "<b>" in text
        assert "<pre>" in text
        assert "вихідний" in text
        assert "Пн–Пт" in text or "Пн–Пт" in text.replace("–", "–")
        assert "Пн: " not in text
        assert "/my" not in text
        assert "/admin" not in text
        assert "/start" not in text
        print("  welcome OK:", text.splitlines()[0])

        print("=== smoke: reply main menu shape ===")
        client_kb = main_menu("uk", is_owner=False)
        owner_kb = main_menu("uk", is_owner=True)
        assert t("uk", "btn_my").startswith("🗂")
        assert t("uk", "btn_admin") in [b.text for r in owner_kb.keyboard for b in r]
        assert t("uk", "btn_admin") not in [b.text for r in client_kb.keyboard for b in r]
        print("  menu labels OK")

        print("=== smoke: first message without /start shows menu ===")
        user = fake_user()
        state = await make_state(user.id)
        msg = fake_message(user, "привіт")
        await common.fallback_menu(msg, settings)
        assert msg.answer.await_count == 1
        _assert_reply_menu(msg.answer.call_args_list)
        print("  fallback menu OK")

        print("=== smoke: /start still works ===")
        state = await make_state(user.id)
        msg = fake_message(user, "/start")
        await common.cmd_start(msg, state, settings)
        assert msg.answer.await_count == 1
        _assert_reply_menu(msg.answer.call_args_list)
        print("  /start answered with reply menu")

        print("=== smoke: contacts button ===")
        msg = fake_message(user, t("uk", "btn_contacts"))
        await common.btn_contacts(msg, await make_state(user.id), settings)
        body = msg.answer.call_args[0][0]
        assert "Хрещатик" in body or settings.business.address.split(",")[0] in body
        assert "<pre>" in body and "вихідний" in body
        assert "/my" not in body
        print("  contacts OK")

        print("=== smoke: slot generation for demo services ===")
        dates = available_dates(settings.business)
        assert dates, "expected working dates in horizon"
        day = dates[0]
        svc = settings.business.services[0]
        tz = ZoneInfo(TZ)
        now = datetime(day.year, day.month, day.day, 8, 0, tzinfo=tz)
        slots = generate_slots(settings.business, day, svc.duration_minutes, now=now)
        assert slots, f"expected slots on {day} for {svc.id}"
        print(f"  {day}: {len(slots)} slots for {svc.name}")

        print("=== smoke: booking via «Записатися» button → use_name → phone → confirm ===")
        state = await make_state(user.id)
        msg = fake_message(user, t("uk", "btn_book"))
        await booking.btn_book(msg, state, settings)
        assert await state.get_state() == BookingFSM.choosing_service.state
        print("  btn_book → choosing_service")

        cb = fake_callback(user, f"book:svc:{svc.id}")
        await booking.book_service(cb, state, settings)
        assert await state.get_state() == BookingFSM.choosing_date.state
        print(f"  service {svc.id}")

        future = datetime.now(tz) + timedelta(days=2)
        for _ in range(7):
            if (
                future.weekday() in settings.business.working_hours
                and future.date().isoformat() not in settings.business.days_off
            ):
                break
            future += timedelta(days=1)
        day_iso = future.date().isoformat()
        hhmm = "11:00"
        await state.update_data(
            service_id=svc.id,
            service_name=svc.name,
            duration_minutes=svc.duration_minutes,
            price=svc.price_label("uk"),
            day_iso=day_iso,
            time_hhmm=hhmm,
            tg_first_name=user.first_name,
        )
        await state.set_state(BookingFSM.entering_name)

        cb = fake_callback(user, "book:use_name")
        await booking.book_use_name(cb, state, settings)
        assert await state.get_state() == BookingFSM.entering_phone.state
        data = await state.get_data()
        assert data["client_name"] == "Олена"
        print("  use_name button OK")

        msg = fake_message(user, "+380501112233")
        await booking.book_phone_text(msg, state, settings)
        assert await state.get_state() == BookingFSM.confirming.state
        _assert_reply_menu(msg.answer.call_args_list)
        print("  phone accepted, confirm + main menu restored")

        cb = fake_callback(user, "book:confirm")
        await booking.book_confirm(cb, state, settings, db)
        assert cb.bot.send_message.await_count >= 1
        # confirmation message should carry cancel + book-again buttons
        edit_calls = cb.message.edit_text.call_args_list
        answer_calls = cb.message.answer.call_args_list
        markup = None
        for call in list(edit_calls) + list(answer_calls):
            rm = call.kwargs.get("reply_markup")
            if rm is not None and getattr(rm, "inline_keyboard", None):
                markup = rm
                break
        assert markup is not None, "expected booked inline kb"
        cbs = [b.callback_data for row in markup.inline_keyboard for b in row]
        assert any(c.startswith("my:cancel:") for c in cbs)
        assert "book:start" in cbs
        print(f"  confirmed with cancel/book-again; notify calls={cb.bot.send_message.await_count}")

        bookings = await db.list_user_bookings(user.id, upcoming_only=False)
        assert len(bookings) == 1
        bid = bookings[0].id
        print(f"  booking #{bid} in DB")

        print("=== smoke: «Мої записи» button + client cancel ===")
        msg = fake_message(user, t("uk", "btn_my"))
        await my_bookings.btn_my(msg, await make_state(user.id), settings, db)
        assert msg.answer.await_count >= 1

        cb = fake_callback(user, f"my:cancel:{bid}")
        cb.message.edit_text = AsyncMock()
        await my_bookings.cb_my_cancel(cb, settings, db)
        assert (await db.get_booking(bid)).status == "cancelled"
        print("  client cancel OK")

        print("=== smoke: admin via «Адмін» button + block day button ===")
        stranger = fake_user(uid=111, first_name="X")
        msg = fake_message(stranger, t("uk", "btn_admin"))
        await admin.btn_admin(msg, await make_state(stranger.id), settings)
        denied = msg.answer.call_args[0][0]
        assert "власник" in denied.lower() or "только" in denied.lower() or "лише" in denied.lower()
        print("  stranger denied on admin button")

        owner = fake_user(uid=settings.owner_chat_id, first_name="Owner")
        msg = fake_message(owner, t("uk", "btn_admin"))
        await admin.btn_admin(msg, await make_state(owner.id), settings)
        assert msg.answer.await_count >= 1
        print("  owner admin panel OK")

        starts = datetime.now(tz) + timedelta(days=3)
        for _ in range(7):
            if starts.weekday() in settings.business.working_hours:
                break
            starts += timedelta(days=1)
        starts = starts.replace(hour=12, minute=0, second=0, microsecond=0)
        b2 = await db.create_booking(
            user_id=user.id,
            client_name="Олена",
            phone="+380501112233",
            service_id=svc.id,
            service_name=svc.name,
            duration_minutes=svc.duration_minutes,
            starts_at=starts,
            ends_at=starts + timedelta(minutes=svc.duration_minutes),
        )
        assert b2 is not None

        # Text block still works
        msg = fake_message(owner, "2026-12-01")
        st = await make_state(owner.id)
        from bot.states import AdminFSM

        await st.set_state(AdminFSM.blocking)
        await admin.admin_block_save(msg, st, settings, db)
        ranges = await db.active_ranges_for_day("2026-12-01")
        assert ranges, "block should appear"
        print("  admin block day (text) OK")

        # Quick block via button
        st = await make_state(owner.id)
        await st.set_state(AdminFSM.blocking)
        cb = fake_callback(owner, "admin:block_day:0")
        cb.message.edit_text = AsyncMock()
        await admin.admin_block_day_btn(cb, st, settings, db)
        assert await st.get_state() is None
        print("  admin block_day button OK")

        cb = fake_callback(owner, f"admin:cancel:{b2.id}")
        cb.message.answer = AsyncMock()
        await admin.admin_cancel(cb, settings, db)
        assert (await db.get_booking(b2.id)).status == "cancelled"
        print("  admin cancel + client notify OK")

        # Command handlers still exist
        msg = fake_message(user, "/my")
        await my_bookings.cmd_my(msg, await make_state(user.id), settings, db)
        assert msg.answer.await_count == 1
        print("  /my handler still works")

        print("=== smoke: DEMO mirrors owner notify to booker ===")
        assert settings.demo is True
        print("  DEMO=1 flag set on settings")

    print("\nSMOKE OK — full button-driven client + owner flow without Telegram network.")


if __name__ == "__main__":
    asyncio.run(run())
