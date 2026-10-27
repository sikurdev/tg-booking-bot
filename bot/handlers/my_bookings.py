from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.config import AppSettings
from bot.formatting import format_when
from bot.db import Database
from bot.handlers.common import reply_menu
from bot.keyboards import my_bookings_kb
from bot.notify import notify_owner_cancel
from bot.texts import all_langs, t

router = Router(name="my_bookings")


async def _render_list(
    target: Message, settings: AppSettings, db: Database, user_id: int, *, edit: bool = False
) -> None:
    lang = settings.business.language
    bookings = await db.list_user_bookings(user_id)
    uid = user_id
    if not bookings:
        text = t(lang, "my_empty")
        if edit:
            try:
                await target.edit_text(text, reply_markup=my_bookings_kb(lang, []))
                return
            except Exception:
                pass
        await target.answer(text, reply_markup=reply_menu(settings, uid))
        return
    lines = [t(lang, "my_list"), ""]
    for b in bookings:
        lines.append(f"#{b.id} · {b.service_name} · {format_when(b.starts_at, lang)}")
    text = "\n".join(lines)
    kb = my_bookings_kb(lang, [b.id for b in bookings])
    if edit:
        try:
            await target.edit_text(text, reply_markup=kb)
            return
        except Exception:
            pass
    await target.answer(text, reply_markup=kb)


@router.message(Command("my"))
async def cmd_my(
    message: Message, state: FSMContext, settings: AppSettings, db: Database
) -> None:
    await state.clear()
    await _render_list(message, settings, db, message.from_user.id)


@router.message(F.text.in_(all_langs("btn_my")))
async def btn_my(
    message: Message, state: FSMContext, settings: AppSettings, db: Database
) -> None:
    await state.clear()
    uid = message.from_user.id if message.from_user else 0
    # Reply menu already visible — single message with the list / empty hint.
    await _render_list(message, settings, db, uid)


@router.callback_query(F.data == "my:list")
async def cb_my_list(callback: CallbackQuery, settings: AppSettings, db: Database) -> None:
    await callback.answer()
    await _render_list(
        callback.message, settings, db, callback.from_user.id, edit=True  # type: ignore[arg-type]
    )


@router.callback_query(F.data.startswith("my:cancel:"))
async def cb_my_cancel(
    callback: CallbackQuery, settings: AppSettings, db: Database
) -> None:
    booking_id = int(callback.data.split(":")[2])  # type: ignore[union-attr]
    lang = settings.business.language
    booking = await db.cancel_booking(booking_id, by_user_id=callback.from_user.id)
    if booking is None:
        await callback.answer("—", show_alert=True)
        return
    await callback.answer()
    try:
        await callback.message.edit_text(t(lang, "cancelled_ok"))  # type: ignore[union-attr]
    except Exception:
        await callback.message.answer(t(lang, "cancelled_ok"))  # type: ignore[union-attr]
    await notify_owner_cancel(callback.bot, settings, booking)
