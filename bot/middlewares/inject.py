from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from bot.config import AppSettings
from bot.db import Database


class InjectMiddleware(BaseMiddleware):
    def __init__(self, settings: AppSettings, db: Database) -> None:
        self.settings = settings
        self.db = db

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        data["settings"] = self.settings
        data["db"] = self.db
        return await handler(event, data)
