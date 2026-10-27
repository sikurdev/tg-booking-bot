"""Owner notifications + demo mirror to the booking user."""

from __future__ import annotations

from aiogram import Bot

from bot.config import AppSettings
from bot.db import Booking
from bot.formatting import format_when
from bot.texts import t


def format_booking_details(settings: AppSettings, booking: Booking) -> str:
    lang = settings.business.language
    return t(
        lang,
        "details",
        business=settings.business.name,
        service=booking.service_name,
        when=format_when(booking.starts_at, lang),
        duration=booking.duration_minutes,
        client_name=booking.client_name,
        phone=booking.phone,
    )


def is_owner_booking(settings: AppSettings, booking: Booking) -> bool:
    return booking.user_id == settings.owner_chat_id


def client_confirmation_text(settings: AppSettings, booking: Booking) -> str:
    """Text shown to the booker after a successful booking.

    When the booker is also the owner, fold the owner notification (and demo
    copy) into one message so they do not receive three nearly-identical ones.
    """
    lang = settings.business.language
    details = format_booking_details(settings, booking)
    booked = t(lang, "booked_ok", details=details)
    if not is_owner_booking(settings, booking):
        return booked
    owner_body = t(lang, "owner_new", details=details)
    return t(lang, "booked_ok_owner_combined", booked=booked, owner_body=owner_body)


async def notify_owner_new(bot: Bot, settings: AppSettings, booking: Booking) -> None:
    """Notify the owner about a new booking.

    Skipped entirely when the booker is the owner — they already got a combined
    confirmation via :func:`client_confirmation_text`.
    """
    if is_owner_booking(settings, booking):
        return
    lang = settings.business.language
    details = format_booking_details(settings, booking)
    body = t(lang, "owner_new", details=details)
    await bot.send_message(settings.owner_chat_id, body)
    if settings.demo:
        await bot.send_message(
            booking.user_id,
            t(lang, "demo_owner_copy", body=body),
        )


async def notify_owner_cancel(bot: Bot, settings: AppSettings, booking: Booking) -> None:
    lang = settings.business.language
    details = format_booking_details(settings, booking)
    body = t(lang, "owner_cancel", details=details)
    if is_owner_booking(settings, booking):
        # Owner cancelled their own booking elsewhere — one message is enough.
        await bot.send_message(settings.owner_chat_id, body)
        return
    await bot.send_message(settings.owner_chat_id, body)
    if settings.demo:
        await bot.send_message(
            booking.user_id,
            t(lang, "demo_owner_copy", body=body),
        )


async def notify_client_cancelled_by_owner(
    bot: Bot, settings: AppSettings, booking: Booking
) -> None:
    if is_owner_booking(settings, booking):
        return
    lang = settings.business.language
    details = format_booking_details(settings, booking)
    await bot.send_message(
        booking.user_id,
        t(lang, "cancel_client_notify", details=details),
    )
