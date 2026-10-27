from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.config import AppSettings
from bot.formatting import format_day_human
from bot.db import Database
from bot.handlers.common import reply_menu, send_home
from bot.keyboards import admin_block_kb, admin_day_kb, admin_kb
from bot.notify import notify_client_cancelled_by_owner, notify_owner_cancel
from bot.slots import parse_block_input
from bot.states import AdminFSM
from bot.texts import all_langs, t

router = Router(name="admin")


def _is_owner(user_id: int, settings: AppSettings) -> bool:
    return user_id == settings.owner_chat_id


async def _show_admin_panel(message: Message, state: FSMContext, settings: AppSettings) -> None:
    lang = settings.business.language
    await state.clear()
    # Reply menu is already visible (owner tapped Адмін) — one message with inline panel.
    await message.answer(t(lang, "admin_header"), reply_markup=admin_kb(lang))


@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext, settings: AppSettings) -> None:
    lang = settings.business.language
    if not _is_owner(message.from_user.id, settings):
        await message.answer(
            t(lang, "admin_denied"),
            reply_markup=reply_menu(settings, message.from_user.id),
        )
        return
    await _show_admin_panel(message, state, settings)


@router.message(F.text.in_(all_langs("btn_admin")))
async def btn_admin(message: Message, state: FSMContext, settings: AppSettings) -> None:
    lang = settings.business.language
    if not _is_owner(message.from_user.id, settings):
        await message.answer(
            t(lang, "admin_denied"),
            reply_markup=reply_menu(settings, message.from_user.id),
        )
        return
    await _show_admin_panel(message, state, settings)


@router.callback_query(F.data == "admin:home")
async def admin_home(callback: CallbackQuery, state: FSMContext, settings: AppSettings) -> None:
    if not _is_owner(callback.from_user.id, settings):
        await callback.answer(t(settings.business.language, "admin_denied"), show_alert=True)
        return
    await callback.answer()
    await state.clear()
    lang = settings.business.language
    try:
        await callback.message.edit_text(t(lang, "admin_header"), reply_markup=admin_kb(lang))  # type: ignore[union-attr]
    except Exception:
        await callback.message.answer(t(lang, "admin_header"), reply_markup=admin_kb(lang))  # type: ignore[union-attr]


@router.callback_query(F.data.startswith("admin:day:"))
async def admin_day(
    callback: CallbackQuery, settings: AppSettings, db: Database
) -> None:
    if not _is_owner(callback.from_user.id, settings):
        await callback.answer(t(settings.business.language, "admin_denied"), show_alert=True)
        return
    await callback.answer()
    offset = int(callback.data.split(":")[2])  # type: ignore[union-attr]
    lang = settings.business.language
    tz = ZoneInfo(settings.timezone)
    day_date = datetime.now(tz).date() + timedelta(days=offset)
    day = day_date.isoformat()
    day_label = format_day_human(day_date, lang)
    bookings = await db.list_bookings_for_day(day)
    if not bookings:
        text = f"{day_label}\n\n{t(lang, 'admin_empty')}"
        try:
            await callback.message.edit_text(text, reply_markup=admin_kb(lang))  # type: ignore[union-attr]
        except Exception:
            await callback.message.answer(text, reply_markup=admin_kb(lang))  # type: ignore[union-attr]
        return
    lines = [f"📅 {day_label}", ""]
    for b in bookings:
        lines.append(
            f"#{b.id} {b.starts_at.strftime('%H:%M')} · {b.service_name} · "
            f"{b.client_name} · {b.phone}"
        )
    try:
        await callback.message.edit_text(  # type: ignore[union-attr]
            "\n".join(lines),
            reply_markup=admin_day_kb(lang, [b.id for b in bookings]),
        )
    except Exception:
        await callback.message.answer(  # type: ignore[union-attr]
            "\n".join(lines),
            reply_markup=admin_day_kb(lang, [b.id for b in bookings]),
        )


@router.callback_query(F.data.startswith("admin:cancel:"))
async def admin_cancel(
    callback: CallbackQuery, settings: AppSettings, db: Database
) -> None:
    if not _is_owner(callback.from_user.id, settings):
        await callback.answer(t(settings.business.language, "admin_denied"), show_alert=True)
        return
    booking_id = int(callback.data.split(":")[2])  # type: ignore[union-attr]
    lang = settings.business.language
    booking = await db.cancel_booking(booking_id)
    if booking is None:
        await callback.answer("—", show_alert=True)
        return
    await callback.answer()
    await callback.message.answer(t(lang, "cancelled_ok") + f" #{booking_id}")  # type: ignore[union-attr]
    await notify_client_cancelled_by_owner(callback.bot, settings, booking)
    await notify_owner_cancel(callback.bot, settings, booking)


@router.callback_query(F.data == "admin:block")
async def admin_block_start(
    callback: CallbackQuery, state: FSMContext, settings: AppSettings
) -> None:
    if not _is_owner(callback.from_user.id, settings):
        await callback.answer(t(settings.business.language, "admin_denied"), show_alert=True)
        return
    await callback.answer()
    lang = settings.business.language
    await state.set_state(AdminFSM.blocking)
    try:
        await callback.message.edit_text(t(lang, "block_ask_day"), reply_markup=admin_block_kb(lang))  # type: ignore[union-attr]
    except Exception:
        await callback.message.answer(  # type: ignore[union-attr]
            t(lang, "block_ask_day"),
            reply_markup=admin_block_kb(lang),
        )


@router.callback_query(F.data.startswith("admin:block_day:"), AdminFSM.blocking)
async def admin_block_day_btn(
    callback: CallbackQuery, state: FSMContext, settings: AppSettings, db: Database
) -> None:
    if not _is_owner(callback.from_user.id, settings):
        await callback.answer(t(settings.business.language, "admin_denied"), show_alert=True)
        return
    await callback.answer()
    offset = int(callback.data.split(":")[2])  # type: ignore[union-attr]
    lang = settings.business.language
    tz = ZoneInfo(settings.timezone)
    day = datetime.now(tz).date() + timedelta(days=offset)
    start = datetime(day.year, day.month, day.day, 0, 0, tzinfo=tz)
    end = start + timedelta(days=1)
    await db.add_block(start, end, reason="admin")
    await state.clear()
    text = (
        t(lang, "block_ok")
        + f"\n{start.strftime('%Y-%m-%d %H:%M')} — {end.strftime('%Y-%m-%d %H:%M')}"
    )
    try:
        await callback.message.edit_text(text, reply_markup=admin_kb(lang))  # type: ignore[union-attr]
    except Exception:
        await callback.message.answer(text, reply_markup=admin_kb(lang))  # type: ignore[union-attr]


@router.message(AdminFSM.blocking, F.text)
async def admin_block_save(
    message: Message, state: FSMContext, settings: AppSettings, db: Database
) -> None:
    if not _is_owner(message.from_user.id, settings):
        return
    lang = settings.business.language
    raw = (message.text or "").strip()
    if raw in all_langs("btn_home"):
        await send_home(message, state, settings)
        return
    if raw in all_langs("btn_admin") or raw in all_langs("btn_back"):
        await _show_admin_panel(message, state, settings)
        return
    tr = parse_block_input(raw, settings.timezone)
    if tr is None:
        await message.answer(t(lang, "block_bad"), reply_markup=admin_block_kb(lang))
        return
    await db.add_block(tr.start, tr.end, reason="admin")
    await state.clear()
    await message.answer(
        t(lang, "block_ok")
        + f"\n{tr.start.strftime('%Y-%m-%d %H:%M')} — {tr.end.strftime('%Y-%m-%d %H:%M')}",
        reply_markup=admin_kb(lang),
    )
