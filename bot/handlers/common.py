from html import escape

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.config import AppSettings
from bot.formatting import format_working_hours_block
from bot.keyboards import main_menu
from bot.texts import all_langs, t

router = Router(name="common")


def is_owner(user_id: int | None, settings: AppSettings) -> bool:
    return user_id is not None and user_id == settings.owner_chat_id


def reply_menu(settings: AppSettings, user_id: int | None):
    return main_menu(settings.business.language, is_owner=is_owner(user_id, settings))


def welcome_text(settings: AppSettings) -> str:
    """Short HTML welcome: name · demo line · address · phone · hours · menu."""
    b = settings.business
    lang = b.language
    parts: list[str] = [f"<b>{escape(b.name)}</b>"]
    if b.welcome_extra:
        parts.append(escape(b.welcome_extra))
    parts.append("")
    parts.append(f"📍 {escape(b.address)}")
    parts.append(f"📞 {escape(b.phone)}")
    parts.append("")
    parts.append(format_working_hours_block(b, lang))
    parts.append("")
    parts.append(escape(t(lang, "menu_hint")))
    return "\n".join(parts)


def contacts_text(settings: AppSettings) -> str:
    b = settings.business
    lang = b.language
    parts = [
        escape(t(lang, "contacts_header")),
        "",
        f"📍 {escape(b.address)}",
        f"📞 {escape(b.phone)}",
        "",
        format_working_hours_block(b, lang),
    ]
    return "\n".join(parts)


async def send_home(message: Message, state: FSMContext, settings: AppSettings) -> None:
    await state.clear()
    uid = message.from_user.id if message.from_user else None
    await message.answer(
        welcome_text(settings),
        reply_markup=reply_menu(settings, uid),
        parse_mode=ParseMode.HTML,
    )


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, settings: AppSettings) -> None:
    await send_home(message, state, settings)


@router.callback_query(F.data == "nav:home")
async def nav_home(callback: CallbackQuery, state: FSMContext, settings: AppSettings) -> None:
    await callback.answer()
    await state.clear()
    uid = callback.from_user.id if callback.from_user else None
    try:
        await callback.message.edit_reply_markup(reply_markup=None)  # type: ignore[union-attr]
    except Exception:
        pass
    await callback.message.answer(  # type: ignore[union-attr]
        welcome_text(settings),
        reply_markup=reply_menu(settings, uid),
        parse_mode=ParseMode.HTML,
    )


@router.message(Command("help"))
async def cmd_help(message: Message, settings: AppSettings) -> None:
    lang = settings.business.language
    uid = message.from_user.id if message.from_user else None
    if lang == "ru":
        text = (
            "Все действия — кнопками внизу экрана.\n"
            "📅 Записаться · 🗂 Мои записи · ℹ️ Контакты"
            + (" · 👤 Админ" if is_owner(uid, settings) else "")
        )
    else:
        text = (
            "Усі дії — кнопками внизу екрана.\n"
            "📅 Записатися · 🗂 Мої записи · ℹ️ Контакти"
            + (" · 👤 Адмін" if is_owner(uid, settings) else "")
        )
    await message.answer(text, reply_markup=reply_menu(settings, uid))


@router.message(F.text.in_(all_langs("btn_contacts")))
async def btn_contacts(message: Message, state: FSMContext, settings: AppSettings) -> None:
    await state.clear()
    uid = message.from_user.id if message.from_user else None
    await message.answer(
        contacts_text(settings),
        reply_markup=reply_menu(settings, uid),
        parse_mode=ParseMode.HTML,
    )


@router.message(F.text.in_(all_langs("btn_home")))
async def btn_home(message: Message, state: FSMContext, settings: AppSettings) -> None:
    await send_home(message, state, settings)


# Catch-all lives on a dedicated router included LAST (see handlers/__init__.py).
fallback_router = Router(name="fallback")


@fallback_router.message(StateFilter(None))
async def fallback_menu(message: Message, settings: AppSettings) -> None:
    """Any idle message shows the menu — buttons only, no commands needed."""
    uid = message.from_user.id if message.from_user else None
    await message.answer(
        welcome_text(settings),
        reply_markup=reply_menu(settings, uid),
        parse_mode=ParseMode.HTML,
    )
