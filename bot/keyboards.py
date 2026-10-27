"""Inline and reply keyboards — button-driven UI, no command typing required."""

from __future__ import annotations

from datetime import date, datetime

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

from bot.config import BusinessConfig
from bot.formatting import format_day_short
from bot.texts import t


def main_menu(lang: str, *, is_owner: bool = False) -> ReplyKeyboardMarkup:
    """Persistent reply keyboard always visible under the chat input."""
    rows: list[list[KeyboardButton]] = [
        [KeyboardButton(text=t(lang, "btn_book"))],
        [KeyboardButton(text=t(lang, "btn_my")), KeyboardButton(text=t(lang, "btn_contacts"))],
    ]
    if is_owner:
        rows.append([KeyboardButton(text=t(lang, "btn_admin"))])
    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        is_persistent=True,
    )


def nav_row(lang: str, back_cb: str) -> list[InlineKeyboardButton]:
    return [
        InlineKeyboardButton(text=t(lang, "btn_back"), callback_data=back_cb),
        InlineKeyboardButton(text=t(lang, "btn_home"), callback_data="nav:home"),
    ]


def services_kb(biz: BusinessConfig) -> InlineKeyboardMarkup:
    lang = biz.language
    rows: list[list[InlineKeyboardButton]] = []
    for s in biz.services:
        label = t(
            lang,
            "service_line",
            name=s.name,
            duration=s.duration_minutes,
            price=s.price_label(lang),
        )
        rows.append([InlineKeyboardButton(text=label, callback_data=f"book:svc:{s.id}")])
    rows.append(nav_row(lang, "nav:home"))
    return InlineKeyboardMarkup(inline_keyboard=rows)


def dates_kb(lang: str, dates: list[date]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for d in dates:
        label = format_day_short(d, lang)
        row.append(InlineKeyboardButton(text=label, callback_data=f"book:date:{d.isoformat()}"))
        if len(row) == 3:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append(nav_row(lang, "book:start"))
    return InlineKeyboardMarkup(inline_keyboard=rows)


def times_kb(lang: str, slots: list[datetime], day_iso: str) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for slot in slots:
        label = slot.strftime("%H:%M")
        row.append(
            InlineKeyboardButton(
                text=label,
                callback_data=f"book:time:{day_iso}:{label}",
            )
        )
        if len(row) == 4:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append(nav_row(lang, "book:svc_back"))
    return InlineKeyboardMarkup(inline_keyboard=rows)


def name_kb(lang: str, tg_first_name: str | None = None) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if tg_first_name and tg_first_name.strip():
        rows.append(
            [
                InlineKeyboardButton(
                    text=t(lang, "btn_use_name", name=tg_first_name.strip()[:40]),
                    callback_data="book:use_name",
                )
            ]
        )
    rows.append(nav_row(lang, "book:name_back"))
    return InlineKeyboardMarkup(inline_keyboard=rows)


def confirm_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t(lang, "btn_confirm"), callback_data="book:confirm"),
            ],
            nav_row(lang, "book:confirm_back"),
        ]
    )


def booked_kb(lang: str, booking_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(lang, "btn_cancel_booking"),
                    callback_data=f"my:cancel:{booking_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(lang, "btn_book_again"),
                    callback_data="book:start",
                )
            ],
        ]
    )


def phone_kb(lang: str) -> ReplyKeyboardMarkup:
    """Contact-share keyboard with back/home as reply buttons (typed phone still works)."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t(lang, "btn_share_phone"), request_contact=True)],
            [
                KeyboardButton(text=t(lang, "btn_back")),
                KeyboardButton(text=t(lang, "btn_home")),
            ],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
    )


def remove_kb() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()


def my_bookings_kb(lang: str, booking_ids: list[int]) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=f"{t(lang, 'btn_cancel_booking')} #{bid}",
                callback_data=f"my:cancel:{bid}",
            )
        ]
        for bid in booking_ids
    ]
    rows.append(nav_row(lang, "nav:home"))
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "admin_today"), callback_data="admin:day:0")],
            [InlineKeyboardButton(text=t(lang, "admin_tomorrow"), callback_data="admin:day:1")],
            [InlineKeyboardButton(text=t(lang, "admin_block"), callback_data="admin:block")],
            [InlineKeyboardButton(text=t(lang, "admin_cancel"), callback_data="nav:home")],
        ]
    )


def admin_day_kb(lang: str, booking_ids: list[int]) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=f"{t(lang, 'admin_cancel_booking')} #{bid}",
                callback_data=f"admin:cancel:{bid}",
            )
        ]
        for bid in booking_ids
    ]
    rows.append(nav_row(lang, "admin:home"))
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_block_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "block_today"), callback_data="admin:block_day:0")],
            [InlineKeyboardButton(text=t(lang, "block_tomorrow"), callback_data="admin:block_day:1")],
            nav_row(lang, "admin:home"),
        ]
    )
