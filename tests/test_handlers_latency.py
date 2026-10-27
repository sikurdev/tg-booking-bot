"""Callback answer-before-edit order and single-message menu taps."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from zoneinfo import ZoneInfo

import pytest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup

from bot.config import AppSettings, load_business_config
from bot.db import Database
from bot.handlers import admin, booking, common, my_bookings
from bot.states import BookingFSM
from bot.texts import t

TZ = "Europe/Kyiv"
ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def settings(tmp_path: Path) -> AppSettings:
    biz = load_business_config(ROOT / "config" / "demo_salon.yaml", timezone=TZ)
    return AppSettings(
        bot_token="000000:TEST",
        owner_chat_id=999001,
        business_config_path=ROOT / "config" / "demo_salon.yaml",
        database_path=tmp_path / "t.db",
        demo=True,
        timezone=TZ,
        business=biz,
    )


@pytest.fixture
async def db(tmp_path: Path) -> Database:
    database = Database(tmp_path / "t.db", timezone=TZ)
    await database.init()
    return database


def _user(uid: int = 4242, first_name: str = "Олена"):
    u = MagicMock()
    u.id = uid
    u.first_name = first_name
    u.full_name = first_name
    u.username = "u"
    return u


async def _state(uid: int = 4242) -> FSMContext:
    storage = MemoryStorage()
    return FSMContext(storage=storage, key=StorageKey(bot_id=1, chat_id=uid, user_id=uid))


def _msg(user, text: str = ""):
    m = MagicMock()
    m.from_user = user
    m.text = text
    m.contact = None
    m.answer = AsyncMock()
    m.bot = MagicMock()
    m.bot.send_message = AsyncMock()
    return m


class OrderTracker:
    def __init__(self) -> None:
        self.events: list[str] = []

    def track(self, name: str, mock: AsyncMock) -> None:
        tracker = self

        async def _side(*_a, **_k):
            tracker.events.append(name)
            return MagicMock()

        mock.side_effect = _side


def _cb(user, data: str, tracker: OrderTracker | None = None):
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
    if tracker is not None:
        tracker.track("callback.answer", cb.answer)
        tracker.track("edit_text", cb.message.edit_text)
        tracker.track("edit_reply_markup", cb.message.edit_reply_markup)
        tracker.track("msg.answer", cb.message.answer)
        tracker.track("send_message", cb.bot.send_message)
    return cb


def _assert_answer_first(events: list[str]) -> None:
    assert events, "expected tracked API calls"
    assert events[0] == "callback.answer", f"callback.answer must be first, got {events}"


@pytest.mark.asyncio
async def test_book_start_answers_before_edit(settings: AppSettings):
    tr = OrderTracker()
    user = _user()
    cb = _cb(user, "book:start", tr)
    await booking.book_start(cb, await _state(), settings)
    _assert_answer_first(tr.events)
    assert cb.answer.await_count == 1


@pytest.mark.asyncio
async def test_book_service_answers_before_edit(settings: AppSettings):
    tr = OrderTracker()
    user = _user()
    state = await _state()
    await state.set_state(BookingFSM.choosing_service)
    svc = settings.business.services[0]
    cb = _cb(user, f"book:svc:{svc.id}", tr)
    await booking.book_service(cb, state, settings)
    _assert_answer_first(tr.events)
    assert "show_alert" not in (cb.answer.await_args.kwargs if cb.answer.await_args else {})


@pytest.mark.asyncio
async def test_book_service_alert_on_bad_id(settings: AppSettings):
    user = _user()
    cb = _cb(user, "book:svc:nope")
    await booking.book_service(cb, await _state(), settings)
    assert cb.answer.await_count == 1
    assert cb.answer.await_args.kwargs.get("show_alert") is True
    assert cb.message.edit_text.await_count == 0


@pytest.mark.asyncio
async def test_nav_home_answers_before_work(settings: AppSettings):
    tr = OrderTracker()
    cb = _cb(_user(), "nav:home", tr)
    await common.nav_home(cb, await _state(), settings)
    _assert_answer_first(tr.events)


@pytest.mark.asyncio
async def test_admin_home_answers_before_edit(settings: AppSettings):
    tr = OrderTracker()
    owner = _user(uid=settings.owner_chat_id)
    cb = _cb(owner, "admin:home", tr)
    await admin.admin_home(cb, await _state(owner.id), settings)
    _assert_answer_first(tr.events)


@pytest.mark.asyncio
async def test_book_confirm_answers_before_edit(settings: AppSettings, db: Database):
    tr = OrderTracker()
    user = _user()
    state = await _state()
    await state.set_state(BookingFSM.confirming)
    tz = ZoneInfo(TZ)
    day = datetime.now(tz).date() + timedelta(days=3)
    for _ in range(7):
        if day.weekday() in settings.business.working_hours:
            break
        day += timedelta(days=1)
    svc = settings.business.services[0]
    await state.update_data(
        service_id=svc.id,
        service_name=svc.name,
        duration_minutes=svc.duration_minutes,
        day_iso=day.isoformat(),
        time_hhmm="12:00",
        client_name="Олена",
        phone="+380501112233",
    )
    cb = _cb(user, "book:confirm", tr)
    await booking.book_confirm(cb, state, settings, db)
    _assert_answer_first(tr.events)


@pytest.mark.asyncio
async def test_btn_book_single_message(settings: AppSettings):
    user = _user()
    msg = _msg(user, t("uk", "btn_book"))
    await booking.btn_book(msg, await _state(), settings)
    assert msg.answer.await_count == 1
    kwargs = msg.answer.await_args.kwargs
    assert isinstance(kwargs.get("reply_markup"), InlineKeyboardMarkup)


@pytest.mark.asyncio
async def test_btn_admin_single_message(settings: AppSettings):
    owner = _user(uid=settings.owner_chat_id)
    msg = _msg(owner, t("uk", "btn_admin"))
    await admin.btn_admin(msg, await _state(owner.id), settings)
    assert msg.answer.await_count == 1
    assert isinstance(msg.answer.await_args.kwargs.get("reply_markup"), InlineKeyboardMarkup)


@pytest.mark.asyncio
async def test_btn_my_single_message(settings: AppSettings, db: Database):
    user = _user()
    msg = _msg(user, t("uk", "btn_my"))
    await my_bookings.btn_my(msg, await _state(), settings, db)
    assert msg.answer.await_count == 1


@pytest.mark.asyncio
async def test_phone_confirm_restores_reply_menu(settings: AppSettings):
    """After phone_kb, restore reply menu + confirm inline requires two sends."""
    user = _user()
    state = await _state()
    await state.set_state(BookingFSM.entering_phone)
    tz = ZoneInfo(TZ)
    day = datetime.now(tz).date() + timedelta(days=2)
    svc = settings.business.services[0]
    await state.update_data(
        service_id=svc.id,
        service_name=svc.name,
        duration_minutes=svc.duration_minutes,
        day_iso=day.isoformat(),
        time_hhmm="11:00",
        client_name="Олена",
    )
    msg = _msg(user, "+380501112233")
    await booking.book_phone_text(msg, state, settings)
    assert msg.answer.await_count == 2
    first_rm = msg.answer.await_args_list[0].kwargs.get("reply_markup")
    second_rm = msg.answer.await_args_list[1].kwargs.get("reply_markup")
    assert isinstance(first_rm, ReplyKeyboardMarkup)
    assert isinstance(second_rm, InlineKeyboardMarkup)


@pytest.mark.asyncio
async def test_prompt_services_restore_flag(settings: AppSettings):
    user = _user()
    msg = _msg(user)
    state = await _state()
    await booking._prompt_services(msg, state, settings, restore_reply_menu=True)
    assert msg.answer.await_count == 2


def test_polling_timeouts_tuned():
    from bot.main import POLLING_TIMEOUT, SESSION_TIMEOUT

    assert POLLING_TIMEOUT == 15
    assert SESSION_TIMEOUT == 5.0
    # aiogram request_timeout for getUpdates = session + polling ≈ 20s
    assert SESSION_TIMEOUT + POLLING_TIMEOUT <= 20.0
    assert SESSION_TIMEOUT + POLLING_TIMEOUT >= 15.0
    assert SESSION_TIMEOUT < POLLING_TIMEOUT  # request timeout exceeds polling wait
