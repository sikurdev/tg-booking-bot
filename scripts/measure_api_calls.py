#!/usr/bin/env python3
"""Count Telegram API-ish calls per common action via mocked bot/message.

Reports answer/edit/callback.answer counts for reply-menu taps and key callbacks.
"""
from __future__ import annotations

import asyncio
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, call
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.base import StorageKey

from bot.config import AppSettings, load_business_config
from bot.db import Database
from bot.handlers import common, booking, my_bookings, admin
from bot.states import BookingFSM
from bot.texts import t

TZ = "Europe/Kyiv"


def make_settings(db_path: Path) -> AppSettings:
    biz = load_business_config(ROOT / "config" / "demo_salon.yaml", timezone=TZ)
    return AppSettings(
        bot_token="000000:TEST-MEASURE-TOKEN-NOT-REAL",
        owner_chat_id=999001,
        business_config_path=ROOT / "config" / "demo_salon.yaml",
        database_path=db_path,
        demo=True,
        timezone=TZ,
        business=biz,
    )


def fake_user(uid: int = 4242, first_name: str = "Олена"):
    u = MagicMock()
    u.id = uid
    u.full_name = first_name
    u.first_name = first_name
    u.username = "test"
    return u


def fake_message(user, text: str = ""):
    m = MagicMock()
    m.from_user = user
    m.text = text
    m.contact = None
    m.answer = AsyncMock()
    m.edit_text = AsyncMock()
    m.edit_reply_markup = AsyncMock()
    m.bot = MagicMock()
    m.bot.send_message = AsyncMock()
    return m


def fake_callback(user, data: str):
    cb = MagicMock()
    cb.from_user = user
    cb.data = data
    cb.answer = AsyncMock()
    cb.bot = MagicMock()
    cb.bot.send_message = AsyncMock()
    cb.message = MagicMock()
    cb.message.edit_text = AsyncMock()
    cb.message.edit_reply_markup = AsyncMock()
    cb.message.answer = AsyncMock()
    return cb


async def make_state(user_id: int = 4242) -> FSMContext:
    storage = MemoryStorage()
    key = StorageKey(bot_id=1, chat_id=user_id, user_id=user_id)
    return FSMContext(storage=storage, key=key)


def count_msg(msg) -> dict[str, int]:
    return {
        "answer": msg.answer.await_count,
        "edit_text": getattr(msg, "edit_text").await_count if hasattr(msg.edit_text, "await_count") else 0,
        "edit_reply_markup": getattr(msg, "edit_reply_markup").await_count
        if hasattr(msg.edit_reply_markup, "await_count")
        else 0,
        "send_message": msg.bot.send_message.await_count,
    }


def count_cb(cb) -> dict[str, int]:
    return {
        "callback_answer": cb.answer.await_count,
        "edit_text": cb.message.edit_text.await_count,
        "edit_reply_markup": cb.message.edit_reply_markup.await_count,
        "answer": cb.message.answer.await_count,
        "send_message": cb.bot.send_message.await_count,
    }


def total(d: dict[str, int]) -> int:
    return sum(d.values())


def answer_before_edit(cb) -> bool | None:
    """Return True if callback.answer was awaited before any edit/answer on message."""
    # Reconstruct order via mock_calls on a shared parent — use side_effect timestamps.
    # AsyncMock records await_args_list but not cross-mock order. Use call wrappers.
    return None  # filled by instrumented run below


class OrderTracker:
    def __init__(self):
        self.events: list[str] = []

    def track(self, name: str, mock: AsyncMock) -> AsyncMock:
        tracker = self

        async def _side(*a, **k):
            tracker.events.append(name)
            return MagicMock()

        mock.side_effect = _side
        return mock


async def run() -> None:
    results: list[tuple[str, dict[str, int], list[str] | None]] = []

    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "m.db"
        settings = make_settings(db_path)
        db = Database(db_path, timezone=TZ)
        await db.init()
        user = fake_user()
        owner = fake_user(uid=settings.owner_chat_id, first_name="Owner")
        svc = settings.business.services[0]
        tz = ZoneInfo(TZ)

        # --- reply menu: Book ---
        state = await make_state(user.id)
        msg = fake_message(user, t("uk", "btn_book"))
        await booking.btn_book(msg, state, settings)
        results.append(("btn_book (Записатися)", count_msg(msg), None))

        # --- callback: book:start ---
        ot = OrderTracker()
        state = await make_state(user.id)
        cb = fake_callback(user, "book:start")
        ot.track("callback.answer", cb.answer)
        ot.track("edit_text", cb.message.edit_text)
        ot.track("msg.answer", cb.message.answer)
        await booking.book_start(cb, state, settings)
        results.append(("cb book:start", count_cb(cb), ot.events))

        # --- callback: book:svc ---
        ot = OrderTracker()
        state = await make_state(user.id)
        await state.set_state(BookingFSM.choosing_service)
        cb = fake_callback(user, f"book:svc:{svc.id}")
        ot.track("callback.answer", cb.answer)
        ot.track("edit_text", cb.message.edit_text)
        ot.track("msg.answer", cb.message.answer)
        await booking.book_service(cb, state, settings)
        results.append(("cb book:svc", count_cb(cb), ot.events))

        # --- reply: contacts ---
        msg = fake_message(user, t("uk", "btn_contacts"))
        await common.btn_contacts(msg, await make_state(user.id), settings)
        results.append(("btn_contacts", count_msg(msg), None))

        # --- reply: my bookings (with one booking) ---
        starts = datetime.now(tz) + timedelta(days=3)
        for _ in range(7):
            if starts.weekday() in settings.business.working_hours:
                break
            starts += timedelta(days=1)
        starts = starts.replace(hour=12, minute=0, second=0, microsecond=0)
        await db.create_booking(
            user_id=user.id,
            client_name="Олена",
            phone="+380501112233",
            service_id=svc.id,
            service_name=svc.name,
            duration_minutes=svc.duration_minutes,
            starts_at=starts,
            ends_at=starts + timedelta(minutes=svc.duration_minutes),
        )
        msg = fake_message(user, t("uk", "btn_my"))
        await my_bookings.btn_my(msg, await make_state(user.id), settings, db)
        results.append(("btn_my (Мої записи)", count_msg(msg), None))

        # --- reply: admin ---
        msg = fake_message(owner, t("uk", "btn_admin"))
        await admin.btn_admin(msg, await make_state(owner.id), settings)
        results.append(("btn_admin", count_msg(msg), None))

        # --- callback: nav:home ---
        ot = OrderTracker()
        cb = fake_callback(user, "nav:home")
        ot.track("callback.answer", cb.answer)
        ot.track("edit_reply_markup", cb.message.edit_reply_markup)
        ot.track("msg.answer", cb.message.answer)
        await common.nav_home(cb, await make_state(user.id), settings)
        results.append(("cb nav:home", count_cb(cb), ot.events))

        # --- phone → confirm (restore reply menu path) ---
        state = await make_state(user.id)
        await state.set_state(BookingFSM.entering_phone)
        await state.update_data(
            service_id=svc.id,
            service_name=svc.name,
            duration_minutes=svc.duration_minutes,
            price="x",
            day_iso=starts.date().isoformat(),
            time_hhmm="12:00",
            client_name="Олена",
        )
        msg = fake_message(user, "+380501112233")
        await booking.book_phone_text(msg, state, settings)
        results.append(("phone→confirm", count_msg(msg), None))

        # --- callback: book:confirm ---
        ot = OrderTracker()
        state = await make_state(user.id)
        await state.set_state(BookingFSM.confirming)
        await state.update_data(
            service_id=svc.id,
            service_name=svc.name,
            duration_minutes=svc.duration_minutes,
            day_iso=(starts + timedelta(days=1)).date().isoformat(),
            time_hhmm="13:00",
            client_name="Олена",
            phone="+380501112233",
        )
        # ensure day is open-ish; create_booking may still work
        day2 = starts + timedelta(days=1)
        for _ in range(7):
            if day2.weekday() in settings.business.working_hours:
                break
            day2 += timedelta(days=1)
        await state.update_data(day_iso=day2.date().isoformat())
        cb = fake_callback(user, "book:confirm")
        ot.track("callback.answer", cb.answer)
        ot.track("edit_text", cb.message.edit_text)
        ot.track("msg.answer", cb.message.answer)
        ot.track("send_message", cb.bot.send_message)
        await booking.book_confirm(cb, state, settings, db)
        results.append(("cb book:confirm", count_cb(cb), ot.events))

    print("action\tapi_calls\tbreakdown\tcallback_order")
    for name, counts, events in results:
        order = ""
        if events is not None:
            order = " → ".join(events) if events else "(none)"
            # flag if answer not first among callback ops
            cb_ops = [e for e in events if e.startswith("callback") or e.startswith("edit") or e.startswith("msg")]
            if cb_ops and cb_ops[0] != "callback.answer":
                order += "  [ANSWER_NOT_FIRST]"
        print(f"{name}\t{total(counts)}\t{counts}\t{order}")


if __name__ == "__main__":
    asyncio.run(run())
