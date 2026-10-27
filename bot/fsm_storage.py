"""SQLite-backed FSM storage for aiogram 3 (survives process restarts)."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import aiosqlite
from aiogram.exceptions import DataNotDictLikeError
from aiogram.fsm.state import State
from aiogram.fsm.storage.base import BaseStorage, StateType, StorageKey

SCHEMA = """
CREATE TABLE IF NOT EXISTS fsm (
    bot_id INTEGER NOT NULL,
    chat_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    thread_id INTEGER NOT NULL,
    destiny TEXT NOT NULL,
    state TEXT,
    data TEXT NOT NULL DEFAULT '{}',
    PRIMARY KEY (bot_id, chat_id, user_id, thread_id, destiny)
);
"""


def _thread_id(key: StorageKey) -> int:
    return key.thread_id if key.thread_id is not None else 0


class SQLiteStorage(BaseStorage):
    """Persist FSM state and data in a SQLite file under ``data/``."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._db: aiosqlite.Connection | None = None
        self._lock = asyncio.Lock()

    async def _ensure_db(self) -> aiosqlite.Connection:
        if self._db is None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._db = await aiosqlite.connect(self.path)
            self._db.row_factory = aiosqlite.Row
            await self._db.execute("PRAGMA journal_mode=WAL")
            await self._db.executescript(SCHEMA)
            await self._db.commit()
        return self._db

    async def set_state(self, key: StorageKey, state: StateType = None) -> None:
        state_s = state.state if isinstance(state, State) else state
        async with self._lock:
            db = await self._ensure_db()
            await db.execute(
                """
                INSERT INTO fsm (bot_id, chat_id, user_id, thread_id, destiny, state, data)
                VALUES (?, ?, ?, ?, ?, ?, '{}')
                ON CONFLICT(bot_id, chat_id, user_id, thread_id, destiny)
                DO UPDATE SET state = excluded.state
                """,
                (key.bot_id, key.chat_id, key.user_id, _thread_id(key), key.destiny, state_s),
            )
            await db.commit()

    async def get_state(self, key: StorageKey) -> str | None:
        async with self._lock:
            db = await self._ensure_db()
            cur = await db.execute(
                """
                SELECT state FROM fsm
                WHERE bot_id=? AND chat_id=? AND user_id=? AND thread_id=? AND destiny=?
                """,
                (key.bot_id, key.chat_id, key.user_id, _thread_id(key), key.destiny),
            )
            row = await cur.fetchone()
            return None if row is None else row["state"]

    async def set_data(self, key: StorageKey, data: Mapping[str, Any]) -> None:
        if not isinstance(data, dict):
            msg = f"Data must be a dict or dict-like object, got {type(data).__name__}"
            raise DataNotDictLikeError(msg)
        payload = json.dumps(dict(data), ensure_ascii=False)
        async with self._lock:
            db = await self._ensure_db()
            await db.execute(
                """
                INSERT INTO fsm (bot_id, chat_id, user_id, thread_id, destiny, state, data)
                VALUES (?, ?, ?, ?, ?, NULL, ?)
                ON CONFLICT(bot_id, chat_id, user_id, thread_id, destiny)
                DO UPDATE SET data = excluded.data
                """,
                (key.bot_id, key.chat_id, key.user_id, _thread_id(key), key.destiny, payload),
            )
            await db.commit()

    async def get_data(self, key: StorageKey) -> dict[str, Any]:
        async with self._lock:
            db = await self._ensure_db()
            cur = await db.execute(
                """
                SELECT data FROM fsm
                WHERE bot_id=? AND chat_id=? AND user_id=? AND thread_id=? AND destiny=?
                """,
                (key.bot_id, key.chat_id, key.user_id, _thread_id(key), key.destiny),
            )
            row = await cur.fetchone()
            if row is None:
                return {}
            raw = row["data"] or "{}"
            parsed = json.loads(raw)
            if not isinstance(parsed, dict):
                return {}
            return parsed

    async def close(self) -> None:
        async with self._lock:
            if self._db is not None:
                await self._db.close()
                self._db = None
