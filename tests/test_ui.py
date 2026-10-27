"""Button-driven UI: reply menu, nav rows, name/phone/booked keyboards."""

from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup

from bot.keyboards import (
    admin_block_kb,
    admin_kb,
    booked_kb,
    confirm_kb,
    dates_kb,
    main_menu,
    my_bookings_kb,
    name_kb,
    phone_kb,
    services_kb,
    times_kb,
)
from bot.texts import TEXTS, all_langs, t


def _flatten_inline(kb: InlineKeyboardMarkup) -> list[str]:
    return [btn.text for row in kb.inline_keyboard for btn in row]


def _flatten_reply(kb: ReplyKeyboardMarkup) -> list[str]:
    return [btn.text for row in kb.keyboard for btn in row]


def _callbacks(kb: InlineKeyboardMarkup) -> list[str]:
    return [btn.callback_data for row in kb.inline_keyboard for btn in row]


def test_main_menu_client_no_admin():
    kb = main_menu("uk", is_owner=False)
    texts = _flatten_reply(kb)
    assert t("uk", "btn_book") in texts
    assert t("uk", "btn_my") in texts
    assert t("uk", "btn_contacts") in texts
    assert t("uk", "btn_admin") not in texts
    assert kb.is_persistent is True


def test_main_menu_owner_has_admin():
    kb = main_menu("uk", is_owner=True)
    texts = _flatten_reply(kb)
    assert t("uk", "btn_admin") in texts


def test_btn_my_emoji():
    assert "🗂" in t("uk", "btn_my")
    assert "🗂" in TEXTS["ru"]["btn_my"]


def test_services_kb_has_back_and_home(biz):
    kb = services_kb(biz)
    texts = _flatten_inline(kb)
    assert t("uk", "btn_back") in texts
    assert t("uk", "btn_home") in texts
    cbs = _callbacks(kb)
    assert "nav:home" in cbs


def test_dates_and_times_nav():
    lang = "uk"
    dates = [date(2026, 11, 2), date(2026, 11, 3)]
    dkb = dates_kb(lang, dates)
    labels = _flatten_inline(dkb)
    assert "Пн, 2 лист." in labels
    assert "Вт, 3 лист." in labels
    assert t(lang, "btn_back") in labels
    assert t(lang, "btn_home") in labels
    assert "book:start" in _callbacks(dkb)
    assert "nav:home" in _callbacks(dkb)

    tz = ZoneInfo("Europe/Kyiv")
    slots = [datetime(2026, 11, 2, 10, 0, tzinfo=tz), datetime(2026, 11, 2, 10, 30, tzinfo=tz)]
    tkb = times_kb(lang, slots, "2026-11-02")
    assert t(lang, "btn_back") in _flatten_inline(tkb)
    assert t(lang, "btn_home") in _flatten_inline(tkb)
    assert "book:svc_back" in _callbacks(tkb)


def test_name_kb_use_telegram_name():
    kb = name_kb("uk", "Олена")
    texts = _flatten_inline(kb)
    assert "Використати: Олена" in texts
    assert "book:use_name" in _callbacks(kb)
    assert t("uk", "btn_back") in texts
    assert t("uk", "btn_home") in texts


def test_name_kb_without_name():
    kb = name_kb("uk", None)
    assert "book:use_name" not in _callbacks(kb)
    assert t("uk", "btn_back") in _flatten_inline(kb)


def test_phone_kb_has_contact_and_nav():
    kb = phone_kb("uk")
    texts = _flatten_reply(kb)
    assert t("uk", "btn_share_phone") in texts
    assert t("uk", "btn_back") in texts
    assert t("uk", "btn_home") in texts
    # first button requests contact
    assert kb.keyboard[0][0].request_contact is True


def test_confirm_and_booked_kb():
    ckb = confirm_kb("uk")
    assert "book:confirm" in _callbacks(ckb)
    assert "book:confirm_back" in _callbacks(ckb)
    assert "nav:home" in _callbacks(ckb)

    bkb = booked_kb("uk", 42)
    texts = _flatten_inline(bkb)
    assert t("uk", "btn_cancel_booking") in texts
    assert t("uk", "btn_book_again") in texts
    assert "my:cancel:42" in _callbacks(bkb)
    assert "book:start" in _callbacks(bkb)


def test_my_bookings_cancel_buttons():
    kb = my_bookings_kb("uk", [7, 8])
    cbs = _callbacks(kb)
    assert "my:cancel:7" in cbs
    assert "my:cancel:8" in cbs
    assert "nav:home" in cbs


def test_admin_kb_fully_buttoned():
    kb = admin_kb("uk")
    texts = _flatten_inline(kb)
    assert t("uk", "admin_today") in texts
    assert t("uk", "admin_tomorrow") in texts
    assert t("uk", "admin_block") in texts
    assert t("uk", "admin_cancel") in texts
    cbs = _callbacks(kb)
    assert "admin:day:0" in cbs
    assert "admin:day:1" in cbs
    assert "admin:block" in cbs
    assert "nav:home" in cbs

    bkb = admin_block_kb("uk")
    assert "admin:block_day:0" in _callbacks(bkb)
    assert "admin:block_day:1" in _callbacks(bkb)


def test_all_langs_helper():
    books = all_langs("btn_book")
    assert "📅 Записатися" in books
    assert "📅 Записаться" in books
