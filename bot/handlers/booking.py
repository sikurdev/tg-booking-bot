from __future__ import annotations

import re
from datetime import date as date_cls
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.config import AppSettings
from bot.formatting import format_when_parts
from bot.db import Database
from bot.handlers.common import reply_menu, send_home
from bot.keyboards import (
    booked_kb,
    confirm_kb,
    dates_kb,
    name_kb,
    phone_kb,
    services_kb,
    times_kb,
)
from bot.notify import client_confirmation_text, notify_owner_new
from bot.slots import available_dates, generate_slots
from bot.states import BookingFSM
from bot.texts import all_langs, t

router = Router(name="booking")

PHONE_RE = re.compile(r"^(?:\+?380|0)\d{9}$|^\+?\d{10,15}$")


def _normalize_phone(raw: str) -> str | None:
    cleaned = re.sub(r"[\s\-()]", "", raw.strip())
    if not PHONE_RE.match(cleaned):
        return None
    if cleaned.startswith("0") and len(cleaned) == 10:
        return "+38" + cleaned
    if cleaned.startswith("380") and not cleaned.startswith("+"):
        return "+" + cleaned
    if not cleaned.startswith("+") and cleaned.isdigit():
        return "+" + cleaned
    return cleaned


def _tg_first_name(user) -> str | None:
    if user is None:
        return None
    name = getattr(user, "first_name", None) or ""
    return name.strip() or None


async def _edit_or_answer(callback: CallbackQuery, text: str, reply_markup) -> None:
    try:
        await callback.message.edit_text(text, reply_markup=reply_markup)  # type: ignore[union-attr]
    except Exception:
        await callback.message.answer(text, reply_markup=reply_markup)  # type: ignore[union-attr]


async def _prompt_services(
    message: Message,
    state: FSMContext,
    settings: AppSettings,
    *,
    restore_reply_menu: bool = False,
) -> None:
    """Show service picker. Re-attach reply menu only when phone_kb (or similar) replaced it."""
    await state.set_state(BookingFSM.choosing_service)
    lang = settings.business.language
    uid = message.from_user.id if message.from_user else None
    if restore_reply_menu:
        # ReplyKeyboard + InlineKeyboard cannot share one message — two sends required.
        await message.answer(t(lang, "choose_service"), reply_markup=reply_menu(settings, uid))
        await message.answer("👇", reply_markup=services_kb(settings.business))
    else:
        await message.answer(t(lang, "choose_service"), reply_markup=services_kb(settings.business))


@router.message(F.text.in_(all_langs("btn_book")))
async def btn_book(message: Message, state: FSMContext, settings: AppSettings) -> None:
    await state.clear()
    await _prompt_services(message, state, settings)


@router.callback_query(F.data == "book:start")
async def book_start(callback: CallbackQuery, state: FSMContext, settings: AppSettings) -> None:
    await callback.answer()
    await state.set_state(BookingFSM.choosing_service)
    lang = settings.business.language
    await _edit_or_answer(callback, t(lang, "choose_service"), services_kb(settings.business))


@router.callback_query(F.data == "book:svc_back")
async def book_svc_back(callback: CallbackQuery, state: FSMContext, settings: AppSettings) -> None:
    await callback.answer()
    data = await state.get_data()
    svc_id = data.get("service_id")
    if svc_id:
        await _show_dates(callback, state, settings, svc_id)
    else:
        await state.set_state(BookingFSM.choosing_service)
        lang = settings.business.language
        await _edit_or_answer(callback, t(lang, "choose_service"), services_kb(settings.business))


@router.callback_query(F.data.startswith("book:svc:"))
async def book_service(callback: CallbackQuery, state: FSMContext, settings: AppSettings) -> None:
    svc_id = callback.data.split(":", 2)[2]  # type: ignore[union-attr]
    svc = settings.business.service_by_id(svc_id)
    if not svc:
        await callback.answer("?", show_alert=True)
        return
    await callback.answer()
    await state.update_data(
        service_id=svc.id,
        service_name=svc.name,
        duration_minutes=svc.duration_minutes,
        price=svc.price_label(settings.business.language),
    )
    await _show_dates(callback, state, settings, svc_id)


async def _show_dates(
    callback: CallbackQuery, state: FSMContext, settings: AppSettings, svc_id: str
) -> None:
    lang = settings.business.language
    dates = available_dates(settings.business)
    await state.set_state(BookingFSM.choosing_date)
    if not dates:
        await _edit_or_answer(callback, t(lang, "no_dates"), services_kb(settings.business))
        return
    await _edit_or_answer(callback, t(lang, "choose_date"), dates_kb(lang, dates))


@router.callback_query(F.data.startswith("book:date:"))
async def book_date(
    callback: CallbackQuery, state: FSMContext, settings: AppSettings, db: Database
) -> None:
    day_iso = callback.data.split(":", 2)[2]  # type: ignore[union-attr]
    data = await state.get_data()
    if "duration_minutes" not in data:
        await book_start(callback, state, settings)
        return
    await callback.answer()
    await state.update_data(day_iso=day_iso)
    data = await state.get_data()
    duration = int(data["duration_minutes"])
    lang = settings.business.language
    tz = ZoneInfo(settings.timezone)

    day = date_cls.fromisoformat(day_iso)
    existing = await db.active_ranges_for_day(day_iso)
    slots = generate_slots(
        settings.business,
        day,
        duration,
        existing=existing,
        now=datetime.now(tz),
        tz_name=settings.timezone,
    )
    await state.set_state(BookingFSM.choosing_time)
    if not slots:
        await _edit_or_answer(
            callback,
            t(lang, "no_slots"),
            dates_kb(lang, available_dates(settings.business)),
        )
        return
    await _edit_or_answer(callback, t(lang, "choose_time"), times_kb(lang, slots, day_iso))


@router.callback_query(F.data.startswith("book:time:"))
async def book_time(callback: CallbackQuery, state: FSMContext, settings: AppSettings) -> None:
    await callback.answer()
    parts = callback.data.split(":")  # type: ignore[union-attr]
    day_iso = parts[2]
    hhmm = f"{parts[3]}:{parts[4]}"
    await state.update_data(day_iso=day_iso, time_hhmm=hhmm)
    await state.set_state(BookingFSM.entering_name)
    lang = settings.business.language
    first = _tg_first_name(callback.from_user)
    if first:
        await state.update_data(tg_first_name=first)
    await _edit_or_answer(callback, t(lang, "ask_name"), name_kb(lang, first))


@router.callback_query(F.data == "book:name_back")
async def book_name_back(
    callback: CallbackQuery, state: FSMContext, settings: AppSettings, db: Database
) -> None:
    data = await state.get_data()
    day_iso = data.get("day_iso")
    if not day_iso or "duration_minutes" not in data:
        await book_start(callback, state, settings)
        return
    await state.set_state(BookingFSM.choosing_date)
    # Reuse date handler by synthesizing callback data (book_date answers itself)
    callback.data = f"book:date:{day_iso}"  # type: ignore[misc]
    await book_date(callback, state, settings, db)


@router.callback_query(F.data == "book:use_name", BookingFSM.entering_name)
async def book_use_name(callback: CallbackQuery, state: FSMContext, settings: AppSettings) -> None:
    data = await state.get_data()
    name = data.get("tg_first_name") or _tg_first_name(callback.from_user)
    if not name or len(str(name).strip()) < 2:
        await callback.answer("?", show_alert=True)
        return
    await callback.answer()
    await state.update_data(client_name=str(name).strip())
    await state.set_state(BookingFSM.entering_phone)
    lang = settings.business.language
    try:
        await callback.message.edit_reply_markup(reply_markup=None)  # type: ignore[union-attr]
    except Exception:
        pass
    await callback.message.answer(  # type: ignore[union-attr]
        t(lang, "ask_phone"),
        reply_markup=phone_kb(lang),
    )


@router.message(BookingFSM.entering_name, F.text)
async def book_name(message: Message, state: FSMContext, settings: AppSettings) -> None:
    raw = (message.text or "").strip()
    lang = settings.business.language
    if raw in all_langs("btn_home"):
        await send_home(message, state, settings)
        return
    if raw in all_langs("btn_book"):
        await state.clear()
        await _prompt_services(message, state, settings)
        return
    if raw in all_langs("btn_back"):
        data = await state.get_data()
        day_iso = data.get("day_iso")
        if day_iso and "duration_minutes" in data:
            await state.set_state(BookingFSM.choosing_date)
            dates = available_dates(settings.business)
            await message.answer(t(lang, "choose_date"), reply_markup=dates_kb(lang, dates))
            return
        await _prompt_services(message, state, settings)
        return
    if raw in (
        all_langs("btn_my")
        | all_langs("btn_contacts")
        | all_langs("btn_admin")
        | all_langs("btn_share_phone")
    ):
        # Interrupt booking; leave state so other handlers can run next time —
        # for this message, clear and re-route book/my/contacts via clear+hint.
        await state.clear()
        await message.answer(
            t(lang, "menu_hint"),
            reply_markup=reply_menu(
                settings, message.from_user.id if message.from_user else None
            ),
        )
        return

    name = raw
    if len(name) < 2:
        first = _tg_first_name(message.from_user)
        await message.answer(t(lang, "ask_name"), reply_markup=name_kb(lang, first))
        return
    await state.update_data(client_name=name)
    await state.set_state(BookingFSM.entering_phone)
    await message.answer(t(lang, "ask_phone"), reply_markup=phone_kb(lang))


@router.message(BookingFSM.entering_phone, F.contact)
async def book_phone_contact(message: Message, state: FSMContext, settings: AppSettings) -> None:
    phone = message.contact.phone_number if message.contact else ""
    await _save_phone_and_confirm(message, state, settings, phone)


@router.message(BookingFSM.entering_phone, F.text)
async def book_phone_text(message: Message, state: FSMContext, settings: AppSettings) -> None:
    raw = (message.text or "").strip()
    lang = settings.business.language
    if raw in all_langs("btn_home"):
        await send_home(message, state, settings)
        return
    if raw in all_langs("btn_back"):
        await state.set_state(BookingFSM.entering_name)
        data = await state.get_data()
        first = data.get("tg_first_name") or _tg_first_name(message.from_user)
        uid = message.from_user.id if message.from_user else None
        # phone_kb replaced reply menu — restore it, then show name picker.
        await message.answer(t(lang, "menu_hint"), reply_markup=reply_menu(settings, uid))
        await message.answer(t(lang, "ask_name"), reply_markup=name_kb(lang, first))
        return
    if raw in all_langs("btn_share_phone"):
        await message.answer(t(lang, "ask_phone"), reply_markup=phone_kb(lang))
        return
    if raw in all_langs("btn_book"):
        await state.clear()
        await _prompt_services(message, state, settings, restore_reply_menu=True)
        return
    await _save_phone_and_confirm(message, state, settings, raw)


async def _save_phone_and_confirm(
    message: Message, state: FSMContext, settings: AppSettings, raw_phone: str
) -> None:
    lang = settings.business.language
    phone = _normalize_phone(raw_phone)
    if not phone:
        await message.answer(t(lang, "invalid_phone"), reply_markup=phone_kb(lang))
        return
    await state.update_data(phone=phone)
    data = await state.get_data()
    day = date_cls.fromisoformat(data["day_iso"])
    details = t(
        lang,
        "details",
        business=settings.business.name,
        service=data["service_name"],
        when=format_when_parts(day, data["time_hhmm"], lang),
        duration=data["duration_minutes"],
        client_name=data["client_name"],
        phone=phone,
    )
    await state.set_state(BookingFSM.confirming)
    uid = message.from_user.id if message.from_user else None
    # phone_kb is showing — restore persistent reply menu, then confirm inline buttons.
    await message.answer(
        f"{t(lang, 'confirm_title')}\n\n{details}",
        reply_markup=reply_menu(settings, uid),
    )
    await message.answer("👇", reply_markup=confirm_kb(lang))


@router.callback_query(F.data == "book:confirm_back", BookingFSM.confirming)
async def book_confirm_back(
    callback: CallbackQuery, state: FSMContext, settings: AppSettings
) -> None:
    await callback.answer()
    await state.set_state(BookingFSM.entering_phone)
    lang = settings.business.language
    try:
        await callback.message.edit_reply_markup(reply_markup=None)  # type: ignore[union-attr]
    except Exception:
        pass
    await callback.message.answer(  # type: ignore[union-attr]
        t(lang, "ask_phone"),
        reply_markup=phone_kb(lang),
    )


@router.callback_query(F.data == "book:confirm", BookingFSM.confirming)
async def book_confirm(
    callback: CallbackQuery, state: FSMContext, settings: AppSettings, db: Database
) -> None:
    await callback.answer()
    data = await state.get_data()
    lang = settings.business.language
    tz = ZoneInfo(settings.timezone)
    starts = datetime.fromisoformat(f"{data['day_iso']}T{data['time_hhmm']}:00").replace(
        tzinfo=tz
    )
    ends = starts + timedelta(minutes=int(data["duration_minutes"]))
    booking = await db.create_booking(
        user_id=callback.from_user.id,
        client_name=data["client_name"],
        phone=data["phone"],
        service_id=data["service_id"],
        service_name=data["service_name"],
        duration_minutes=int(data["duration_minutes"]),
        starts_at=starts,
        ends_at=ends,
    )
    if booking is None:
        await _edit_or_answer(callback, t(lang, "no_slots"), services_kb(settings.business))
        await state.clear()
        return

    text = client_confirmation_text(settings, booking)
    await _edit_or_answer(callback, text, booked_kb(lang, booking.id))
    await notify_owner_new(callback.bot, settings, booking)
    await state.clear()
