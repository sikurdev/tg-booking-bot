"""SQLite persistence via aiosqlite: bookings and blocks."""

from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import AsyncIterator
from zoneinfo import ZoneInfo

import aiosqlite

from bot.slots import TimeRange

SCHEMA = """
CREATE TABLE IF NOT EXISTS bookings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    client_name TEXT NOT NULL,
    phone TEXT NOT NULL,
    service_id TEXT NOT NULL,
    service_name TEXT NOT NULL,
    duration_minutes INTEGER NOT NULL,
    starts_at TEXT NOT NULL,
    ends_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS blocks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    starts_at TEXT NOT NULL,
    ends_at TEXT NOT NULL,
    reason TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_bookings_status_starts ON bookings(status, starts_at);
CREATE INDEX IF NOT EXISTS idx_bookings_user ON bookings(user_id, status);
CREATE INDEX IF NOT EXISTS idx_blocks_range ON blocks(starts_at, ends_at);
"""


@dataclass
class Booking:
    id: int
    user_id: int
    client_name: str
    phone: str
    service_id: str
    service_name: str
    duration_minutes: int
    starts_at: datetime
    ends_at: datetime
    status: str
    created_at: datetime


def _parse_dt(value: str, tz: ZoneInfo) -> datetime:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=tz)
    return dt.astimezone(tz)


def _row_to_booking(row: aiosqlite.Row, tz: ZoneInfo) -> Booking:
    return Booking(
        id=row["id"],
        user_id=row["user_id"],
        client_name=row["client_name"],
        phone=row["phone"],
        service_id=row["service_id"],
        service_name=row["service_name"],
        duration_minutes=row["duration_minutes"],
        starts_at=_parse_dt(row["starts_at"], tz),
        ends_at=_parse_dt(row["ends_at"], tz),
        status=row["status"],
        created_at=_parse_dt(row["created_at"], tz),
    )


class Database:
    def __init__(self, path: Path | str, timezone: str = "Europe/Kyiv") -> None:
        self.path = Path(path)
        self.timezone = timezone
        self._tz = ZoneInfo(timezone)
        self._initialized = False

    @asynccontextmanager
    async def connection(self) -> AsyncIterator[aiosqlite.Connection]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = await aiosqlite.connect(self.path)
        db.row_factory = aiosqlite.Row
        try:
            if not self._initialized:
                await db.executescript(SCHEMA)
                await db.commit()
                self._initialized = True
            yield db
        finally:
            await db.close()

    async def init(self) -> None:
        async with self.connection():
            pass

    async def create_booking(
        self,
        *,
        user_id: int,
        client_name: str,
        phone: str,
        service_id: str,
        service_name: str,
        duration_minutes: int,
        starts_at: datetime,
        ends_at: datetime,
    ) -> Booking | None:
        """Insert booking if no overlap with active bookings/blocks. Returns None on conflict."""
        if starts_at.tzinfo is None:
            starts_at = starts_at.replace(tzinfo=self._tz)
        if ends_at.tzinfo is None:
            ends_at = ends_at.replace(tzinfo=self._tz)

        async with self.connection() as db:
            busy = await self._busy_for_day(db, starts_at.astimezone(self._tz).date().isoformat())
            candidate = TimeRange(starts_at, ends_at)
            if any(candidate.overlaps(b) for b in busy):
                return None

            now = datetime.now(self._tz).isoformat()
            cur = await db.execute(
                """
                INSERT INTO bookings (
                    user_id, client_name, phone, service_id, service_name,
                    duration_minutes, starts_at, ends_at, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active', ?)
                """,
                (
                    user_id,
                    client_name,
                    phone,
                    service_id,
                    service_name,
                    duration_minutes,
                    starts_at.isoformat(),
                    ends_at.isoformat(),
                    now,
                ),
            )
            await db.commit()
            booking_id = cur.lastrowid
            row = await (
                await db.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,))
            ).fetchone()
            return _row_to_booking(row, self._tz)

    async def cancel_booking(self, booking_id: int, *, by_user_id: int | None = None) -> Booking | None:
        async with self.connection() as db:
            if by_user_id is not None:
                row = await (
                    await db.execute(
                        "SELECT * FROM bookings WHERE id = ? AND user_id = ? AND status = 'active'",
                        (booking_id, by_user_id),
                    )
                ).fetchone()
            else:
                row = await (
                    await db.execute(
                        "SELECT * FROM bookings WHERE id = ? AND status = 'active'",
                        (booking_id,),
                    )
                ).fetchone()
            if row is None:
                return None
            await db.execute(
                "UPDATE bookings SET status = 'cancelled' WHERE id = ?",
                (booking_id,),
            )
            await db.commit()
            booking = _row_to_booking(row, self._tz)
            booking.status = "cancelled"
            return booking

    async def get_booking(self, booking_id: int) -> Booking | None:
        async with self.connection() as db:
            row = await (
                await db.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,))
            ).fetchone()
            return _row_to_booking(row, self._tz) if row else None

    async def list_user_bookings(self, user_id: int, *, upcoming_only: bool = True) -> list[Booking]:
        async with self.connection() as db:
            now = datetime.now(self._tz).isoformat()
            if upcoming_only:
                rows = await (
                    await db.execute(
                        """
                        SELECT * FROM bookings
                        WHERE user_id = ? AND status = 'active' AND starts_at >= ?
                        ORDER BY starts_at
                        """,
                        (user_id, now),
                    )
                ).fetchall()
            else:
                rows = await (
                    await db.execute(
                        """
                        SELECT * FROM bookings
                        WHERE user_id = ? AND status = 'active'
                        ORDER BY starts_at
                        """,
                        (user_id,),
                    )
                ).fetchall()
            return [_row_to_booking(r, self._tz) for r in rows]

    async def list_bookings_for_day(self, day_iso: str) -> list[Booking]:
        async with self.connection() as db:
            rows = await (
                await db.execute(
                    """
                    SELECT * FROM bookings
                    WHERE status = 'active' AND starts_at LIKE ?
                    ORDER BY starts_at
                    """,
                    (f"{day_iso}%",),
                )
            ).fetchall()
            return [_row_to_booking(r, self._tz) for r in rows]

    async def active_ranges_for_day(self, day_iso: str) -> list[TimeRange]:
        async with self.connection() as db:
            return await self._busy_for_day(db, day_iso)

    async def add_block(self, starts_at: datetime, ends_at: datetime, reason: str = "") -> int:
        if starts_at.tzinfo is None:
            starts_at = starts_at.replace(tzinfo=self._tz)
        if ends_at.tzinfo is None:
            ends_at = ends_at.replace(tzinfo=self._tz)
        async with self.connection() as db:
            now = datetime.now(self._tz).isoformat()
            cur = await db.execute(
                "INSERT INTO blocks (starts_at, ends_at, reason, created_at) VALUES (?, ?, ?, ?)",
                (starts_at.isoformat(), ends_at.isoformat(), reason, now),
            )
            await db.commit()
            return int(cur.lastrowid)

    async def _busy_for_day(self, db: aiosqlite.Connection, day_iso: str) -> list[TimeRange]:
        bookings = await (
            await db.execute(
                """
                SELECT starts_at, ends_at FROM bookings
                WHERE status = 'active' AND (starts_at LIKE ? OR ends_at LIKE ?)
                """,
                (f"{day_iso}%", f"{day_iso}%"),
            )
        ).fetchall()
        day_start = datetime.fromisoformat(f"{day_iso}T00:00:00").replace(tzinfo=self._tz)
        day_end = day_start.replace(hour=23, minute=59, second=59)
        all_blocks = await (await db.execute("SELECT starts_at, ends_at FROM blocks")).fetchall()

        ranges: list[TimeRange] = []
        for r in bookings:
            ranges.append(
                TimeRange(_parse_dt(r["starts_at"], self._tz), _parse_dt(r["ends_at"], self._tz))
            )
        for r in all_blocks:
            tr = TimeRange(_parse_dt(r["starts_at"], self._tz), _parse_dt(r["ends_at"], self._tz))
            if tr.start < day_end and tr.end > day_start:
                ranges.append(tr)
        return ranges
