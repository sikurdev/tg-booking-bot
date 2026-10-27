"""Typographic helpers for hours, dates and times (Ukrainian / Russian)."""

from __future__ import annotations

from datetime import date, datetime
from html import escape

from bot.config import BusinessConfig, DayHours
from bot.texts import t

MONTHS_GENITIVE: dict[str, list[str]] = {
    "uk": [
        "січня",
        "лютого",
        "березня",
        "квітня",
        "травня",
        "червня",
        "липня",
        "серпня",
        "вересня",
        "жовтня",
        "листопада",
        "грудня",
    ],
    "ru": [
        "января",
        "февраля",
        "марта",
        "апреля",
        "мая",
        "июня",
        "июля",
        "августа",
        "сентября",
        "октября",
        "ноября",
        "декабря",
    ],
}

MONTHS_SHORT: dict[str, list[str]] = {
    "uk": [
        "січ.",
        "лют.",
        "бер.",
        "квіт.",
        "трав.",
        "черв.",
        "лип.",
        "серп.",
        "вер.",
        "жовт.",
        "лист.",
        "груд.",
    ],
    "ru": [
        "янв.",
        "фев.",
        "мар.",
        "апр.",
        "мая",
        "июн.",
        "июл.",
        "авг.",
        "сен.",
        "окт.",
        "ноя.",
        "дек.",
    ],
}

EN_DASH = "–"  # U+2013


def _hours_key(hours: DayHours | None) -> tuple[str, str] | None:
    if hours is None:
        return None
    return (hours.open, hours.close)


def _day_span_label(lang: str, start: int, end: int) -> str:
    if start == end:
        return t(lang, f"weekday_{start}")
    return f"{t(lang, f'weekday_{start}')}{EN_DASH}{t(lang, f'weekday_{end}')}"


def format_working_hours_lines(biz: BusinessConfig, lang: str | None = None) -> list[str]:
    """Collapse consecutive weekdays that share the same open/close (or day off).

    Returns plain text lines like ``Пн–Пт   10:00–19:00`` / ``Нд      вихідний``.
    """
    lang = lang or biz.language
    day_off = t(lang, "day_off")

    # Build (start_day, end_day, key) groups for Mon..Sun.
    groups: list[tuple[int, int, tuple[str, str] | None]] = []
    for day in range(7):
        key = _hours_key(biz.working_hours.get(day))
        if groups and groups[-1][2] == key and groups[-1][1] == day - 1:
            start, _, k = groups[-1]
            groups[-1] = (start, day, k)
        else:
            groups.append((day, day, key))

    # Column width for the day label (at least enough for «Пн–Пт»).
    labels = [_day_span_label(lang, a, b) for a, b, _ in groups]
    col = max((len(lbl) for lbl in labels), default=2)
    col = max(col, 5)

    lines: list[str] = []
    for (start, end, key), label in zip(groups, labels):
        if key is None:
            value = day_off
        else:
            value = f"{key[0]}{EN_DASH}{key[1]}"
        lines.append(f"{label:<{col}}   {value}")
    return lines


def format_working_hours_block(biz: BusinessConfig, lang: str | None = None) -> str:
    """HTML hours block: header + aligned ``<pre>`` body."""
    lang = lang or biz.language
    header = f"🕒 <b>{escape(t(lang, 'hours_header'))}</b>"
    body = "\n".join(format_working_hours_lines(biz, lang))
    return f"{header}\n<pre>{escape(body)}</pre>"


def format_day_human(d: date, lang: str) -> str:
    """e.g. «Ср, 29 жовтня»."""
    pack = MONTHS_GENITIVE.get(lang) or MONTHS_GENITIVE["uk"]
    wd = t(lang, f"weekday_{d.weekday()}")
    return f"{wd}, {d.day} {pack[d.month - 1]}"


def format_day_short(d: date, lang: str) -> str:
    """Compact label for date buttons: «Ср, 29 жовт.»."""
    pack = MONTHS_SHORT.get(lang) or MONTHS_SHORT["uk"]
    wd = t(lang, f"weekday_{d.weekday()}")
    return f"{wd}, {d.day} {pack[d.month - 1]}"


def format_when(dt: datetime, lang: str) -> str:
    """e.g. «Ср, 29 жовтня · 12:00»."""
    return f"{format_day_human(dt.date(), lang)} · {dt.strftime('%H:%M')}"


def format_when_parts(day: date, hhmm: str, lang: str) -> str:
    """Combine a calendar day + HH:MM into the same human form."""
    return f"{format_day_human(day, lang)} · {hhmm}"
