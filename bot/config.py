"""Load environment and per-client business YAML. Secrets never hardcoded."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv


@dataclass(frozen=True)
class Service:
    id: str
    name: str
    duration_minutes: int
    price: str | int | float  # "Ціна за запитом" or numeric

    def price_label(self, lang: str = "uk") -> str:
        if isinstance(self.price, (int, float)):
            return f"{int(self.price)} грн" if lang == "uk" else f"{int(self.price)} грн"
        return str(self.price)


@dataclass(frozen=True)
class DayHours:
    open: str  # "HH:MM"
    close: str


@dataclass
class BusinessConfig:
    name: str
    address: str
    phone: str
    language: str
    slot_step_minutes: int
    booking_horizon_days: int
    working_hours: dict[int, DayHours]
    days_off: list[str]
    services: list[Service]
    demo_note: str = ""
    welcome_extra: str = ""
    timezone: str = "Europe/Kyiv"

    def service_by_id(self, service_id: str) -> Service | None:
        for s in self.services:
            if s.id == service_id:
                return s
        return None


@dataclass
class AppSettings:
    bot_token: str
    owner_chat_id: int
    business_config_path: Path
    database_path: Path
    demo: bool
    timezone: str
    business: BusinessConfig = field(repr=False)


REQUIRED_BUSINESS_KEYS = ("business", "services", "working_hours", "slot_step_minutes", "booking_horizon_days")


def _validate_hhmm(value: str, field_name: str) -> None:
    parts = value.split(":")
    if len(parts) != 2:
        raise ValueError(f"{field_name} must be HH:MM, got {value!r}")
    h, m = int(parts[0]), int(parts[1])
    if not (0 <= h <= 23 and 0 <= m <= 59):
        raise ValueError(f"{field_name} out of range: {value!r}")


def validate_business_dict(raw: dict[str, Any]) -> list[str]:
    """Return a list of validation errors (empty = valid)."""
    errors: list[str] = []
    if not isinstance(raw, dict):
        return ["config root must be a mapping"]

    for key in REQUIRED_BUSINESS_KEYS:
        if key not in raw:
            errors.append(f"missing top-level key: {key}")

    biz = raw.get("business") or {}
    if not isinstance(biz, dict):
        errors.append("business must be a mapping")
    else:
        for k in ("name", "address", "phone"):
            if not biz.get(k):
                errors.append(f"business.{k} is required")

    lang = raw.get("language", "uk")
    if lang not in ("uk", "ru"):
        errors.append("language must be 'uk' or 'ru'")

    step = raw.get("slot_step_minutes")
    if not isinstance(step, int) or step <= 0 or step > 240:
        errors.append("slot_step_minutes must be a positive int <= 240")

    horizon = raw.get("booking_horizon_days")
    if not isinstance(horizon, int) or horizon < 1 or horizon > 90:
        errors.append("booking_horizon_days must be an int 1..90")

    wh = raw.get("working_hours") or {}
    if not isinstance(wh, dict) or not wh:
        errors.append("working_hours must be a non-empty mapping")
    else:
        for day, hours in wh.items():
            try:
                d = int(day)
            except (TypeError, ValueError):
                errors.append(f"working_hours key must be weekday 0..6, got {day!r}")
                continue
            if d < 0 or d > 6:
                errors.append(f"weekday out of range: {d}")
            if hours is None:
                continue
            if not isinstance(hours, dict) or "open" not in hours or "close" not in hours:
                errors.append(f"working_hours[{day}] needs open and close")
                continue
            try:
                _validate_hhmm(str(hours["open"]), f"working_hours[{day}].open")
                _validate_hhmm(str(hours["close"]), f"working_hours[{day}].close")
            except ValueError as e:
                errors.append(str(e))

    services = raw.get("services") or []
    if not isinstance(services, list) or not services:
        errors.append("services must be a non-empty list")
    else:
        ids: set[str] = set()
        for i, svc in enumerate(services):
            if not isinstance(svc, dict):
                errors.append(f"services[{i}] must be a mapping")
                continue
            for k in ("id", "name", "duration_minutes"):
                if k not in svc:
                    errors.append(f"services[{i}].{k} is required")
            sid = svc.get("id")
            if sid in ids:
                errors.append(f"duplicate service id: {sid}")
            ids.add(sid)
            dur = svc.get("duration_minutes")
            if not isinstance(dur, int) or dur <= 0:
                errors.append(f"services[{i}].duration_minutes must be a positive int")
            if "price" not in svc:
                errors.append(f"services[{i}].price is required")

    days_off = raw.get("days_off", [])
    if days_off is not None and not isinstance(days_off, list):
        errors.append("days_off must be a list of YYYY-MM-DD strings")

    return errors


def load_business_config(path: Path | str, timezone: str = "Europe/Kyiv") -> BusinessConfig:
    path = Path(path)
    with path.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    errors = validate_business_dict(raw)
    if errors:
        raise ValueError("Invalid business config:\n- " + "\n- ".join(errors))

    biz = raw["business"]
    working: dict[int, DayHours] = {}
    for day, hours in (raw.get("working_hours") or {}).items():
        if hours is None:
            continue
        working[int(day)] = DayHours(open=str(hours["open"]), close=str(hours["close"]))

    services = [
        Service(
            id=str(s["id"]),
            name=str(s["name"]),
            duration_minutes=int(s["duration_minutes"]),
            price=s["price"],
        )
        for s in raw["services"]
    ]

    return BusinessConfig(
        name=str(biz["name"]),
        address=str(biz["address"]),
        phone=str(biz["phone"]),
        language=str(raw.get("language", "uk")),
        slot_step_minutes=int(raw["slot_step_minutes"]),
        booking_horizon_days=int(raw["booking_horizon_days"]),
        working_hours=working,
        days_off=[str(d) for d in (raw.get("days_off") or [])],
        services=services,
        demo_note=str(biz.get("demo_note") or ""),
        welcome_extra=str(biz.get("welcome_extra") or ""),
        timezone=timezone,
    )


def load_settings(env_file: str | Path | None = None) -> AppSettings:
    if env_file:
        load_dotenv(env_file)
    else:
        load_dotenv()

    token = os.environ.get("BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("BOT_TOKEN is required (set in environment or .env)")

    owner_raw = (
        os.environ.get("OWNER_CHAT_ID", "").strip()
        or os.environ.get("OWNER_TELEGRAM_ID", "").strip()
    )
    if not owner_raw:
        raise RuntimeError("OWNER_CHAT_ID or OWNER_TELEGRAM_ID is required")
    try:
        owner_chat_id = int(owner_raw)
    except ValueError as e:
        raise RuntimeError(
            "OWNER_CHAT_ID / OWNER_TELEGRAM_ID must be an integer Telegram user id"
        ) from e

    config_path = Path(os.environ.get("BUSINESS_CONFIG", "config/demo_salon.yaml"))
    db_path = Path(os.environ.get("DATABASE_PATH", "data/bookings.db"))
    demo = os.environ.get("DEMO", "0").strip() in ("1", "true", "True", "yes", "YES")
    timezone = os.environ.get("TIMEZONE", "Europe/Kyiv").strip() or "Europe/Kyiv"

    business = load_business_config(config_path, timezone=timezone)
    business.timezone = timezone

    return AppSettings(
        bot_token=token,
        owner_chat_id=owner_chat_id,
        business_config_path=config_path,
        database_path=db_path,
        demo=demo,
        timezone=timezone,
        business=business,
    )
