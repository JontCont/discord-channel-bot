import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiosqlite


class GuildSettingsDB:
    """Async SQLite storage for per-guild bot settings."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._db: aiosqlite.Connection | None = None

    async def init(self):
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(self.db_path)
        await self._db.execute(
            """
            CREATE TABLE IF NOT EXISTS guild_settings (
                guild_id   INTEGER NOT NULL,
                setting_key TEXT NOT NULL,
                value_json TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (guild_id, setting_key)
            )
            """
        )
        await self._db.commit()

    async def close(self):
        if self._db:
            await self._db.close()
            self._db = None

    async def get_all(self, guild_id: int) -> dict[str, Any]:
        self._ensure_initialized()
        async with self._db.execute(
            "SELECT setting_key, value_json FROM guild_settings WHERE guild_id = ?",
            (guild_id,),
        ) as cursor:
            rows = await cursor.fetchall()
        return {key: json.loads(value) for key, value in rows}

    async def set_many(self, guild_id: int, settings: dict[str, Any]):
        self._ensure_initialized()
        updated_at = datetime.now(timezone.utc).isoformat()
        await self._db.executemany(
            """
            INSERT INTO guild_settings (guild_id, setting_key, value_json, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(guild_id, setting_key) DO UPDATE SET
                value_json = excluded.value_json,
                updated_at = excluded.updated_at
            """,
            [
                (guild_id, key, json.dumps(value, ensure_ascii=False), updated_at)
                for key, value in settings.items()
            ],
        )
        await self._db.commit()

    def _ensure_initialized(self):
        if self._db is None:
            raise RuntimeError("GuildSettingsDB.init() must be called first")