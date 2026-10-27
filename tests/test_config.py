from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from bot.config import load_business_config, validate_business_dict


def test_demo_config_valid(demo_config_path: Path) -> None:
    biz = load_business_config(demo_config_path)
    assert biz.name == "Демо-салон"
    assert biz.language == "uk"
    assert biz.slot_step_minutes == 30
    assert biz.booking_horizon_days == 14
    assert len(biz.services) >= 3
    assert biz.demo_note
    assert "Демо" in biz.welcome_extra or "Дмитр" in biz.welcome_extra


def test_validate_missing_keys() -> None:
    errors = validate_business_dict({})
    assert any("business" in e for e in errors)
    assert any("services" in e for e in errors)


def test_validate_bad_language() -> None:
    raw = yaml.safe_load(Path("config/demo_salon.yaml").read_text(encoding="utf-8"))
    raw["language"] = "en"
    errors = validate_business_dict(raw)
    assert any("language" in e for e in errors)


def test_validate_duplicate_service_ids() -> None:
    raw = yaml.safe_load(Path("config/demo_salon.yaml").read_text(encoding="utf-8"))
    raw["services"].append(dict(raw["services"][0]))
    errors = validate_business_dict(raw)
    assert any("duplicate" in e for e in errors)


def test_validate_bad_hours() -> None:
    raw = yaml.safe_load(Path("config/demo_salon.yaml").read_text(encoding="utf-8"))
    raw["working_hours"][0] = {"open": "25:00", "close": "19:00"}
    errors = validate_business_dict(raw)
    assert errors


def test_load_rejects_invalid(tmp_path: Path) -> None:
    p = tmp_path / "bad.yaml"
    p.write_text("business: {}\nservices: []\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_business_config(p)


def test_owner_telegram_id_accepted(monkeypatch, demo_config_path, tmp_path) -> None:
    from bot.config import load_settings

    monkeypatch.setenv("BOT_TOKEN", "1:TEST")
    monkeypatch.delenv("OWNER_CHAT_ID", raising=False)
    monkeypatch.setenv("OWNER_TELEGRAM_ID", "424242")
    monkeypatch.setenv("BUSINESS_CONFIG", str(demo_config_path))
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "t.db"))
    monkeypatch.setenv("DEMO", "0")
    s = load_settings()
    assert s.owner_chat_id == 424242


def test_owner_chat_id_preferred(monkeypatch, demo_config_path, tmp_path) -> None:
    from bot.config import load_settings

    monkeypatch.setenv("BOT_TOKEN", "1:TEST")
    monkeypatch.setenv("OWNER_CHAT_ID", "111")
    monkeypatch.setenv("OWNER_TELEGRAM_ID", "222")
    monkeypatch.setenv("BUSINESS_CONFIG", str(demo_config_path))
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "t.db"))
    s = load_settings()
    assert s.owner_chat_id == 111
