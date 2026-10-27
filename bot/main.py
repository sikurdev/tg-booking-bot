"""Entry point: long-polling Telegram booking bot."""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.types import BotCommand, MenuButtonCommands

from bot.config import load_settings
from bot.db import Database
from bot.fsm_storage import SQLiteStorage
from bot.handlers import setup_routers
from bot.middlewares import InjectMiddleware

# Long-poll wait; stalled getUpdates abandoned at session.timeout + polling_timeout.
POLLING_TIMEOUT = 15
# Per-request session timeout for ordinary API calls; also the margin added on top of
# polling_timeout for getUpdates (aiogram sets request_timeout = session + polling).
SESSION_TIMEOUT = 5.0  # → stalled getUpdates abandoned within ~20 s


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stdout,
    )


def _fsm_path(database_path: Path) -> Path:
    override = os.environ.get("FSM_STORAGE_PATH", "").strip()
    if override:
        return Path(override)
    return database_path.parent / "fsm.db"


async def _setup_bot_menu(bot: Bot, language: str) -> None:
    """Clients never need commands — keep only /start in the command menu."""
    if language == "ru":
        start_desc = "Меню"
    else:
        start_desc = "Меню"
    await bot.set_my_commands([BotCommand(command="start", description=start_desc)])
    await bot.set_chat_menu_button(menu_button=MenuButtonCommands())


async def run() -> None:
    setup_logging()
    settings = load_settings()
    db = Database(settings.database_path, timezone=settings.timezone)
    await db.init()

    storage = SQLiteStorage(_fsm_path(settings.database_path))
    session = AiohttpSession(timeout=SESSION_TIMEOUT)
    bot = Bot(token=settings.bot_token, session=session)
    dp = Dispatcher(storage=storage)
    inject = InjectMiddleware(settings, db)
    dp.message.middleware(inject)
    dp.callback_query.middleware(inject)
    dp.include_router(setup_routers())

    await _setup_bot_menu(bot, settings.business.language)

    logging.getLogger(__name__).info(
        "Starting bot for %r (demo=%s, config=%s, fsm=%s, polling_timeout=%s, session_timeout=%s)",
        settings.business.name,
        settings.demo,
        settings.business_config_path,
        storage.path,
        POLLING_TIMEOUT,
        SESSION_TIMEOUT,
    )
    try:
        await dp.start_polling(bot, polling_timeout=POLLING_TIMEOUT)
    finally:
        await storage.close()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
