from pathlib import Path

import aiosqlite


class IntroductionDB:
    def __init__(self, path: str):
        self._path = path
        self._db: aiosqlite.Connection | None = None

    async def init(self):
        if self._path != ":memory:":
            Path(self._path).parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(self._path)
        await self._db.executescript(
            """
            CREATE TABLE IF NOT EXISTS introductions (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                message_id INTEGER NOT NULL,
                PRIMARY KEY (guild_id, user_id)
            );
            CREATE TABLE IF NOT EXISTS introduction_panels (
                guild_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                message_id INTEGER NOT NULL,
                PRIMARY KEY (guild_id, channel_id)
            );
            """
        )
        await self._db.commit()

    async def close(self):
        if self._db is not None:
            await self._db.close()
            self._db = None

    @property
    def connection(self) -> aiosqlite.Connection:
        if self._db is None:
            raise RuntimeError("IntroductionDB is not initialized")
        return self._db

    async def get(self, guild_id: int, user_id: int) -> tuple[int, int] | None:
        async with self.connection.execute(
            "SELECT channel_id, message_id FROM introductions "
            "WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        ) as cursor:
            row = await cursor.fetchone()
        return (row[0], row[1]) if row is not None else None

    async def save(
        self, guild_id: int, user_id: int, channel_id: int, message_id: int
    ):
        await self.connection.execute(
            "INSERT INTO introductions (guild_id, user_id, channel_id, message_id) "
            "VALUES (?, ?, ?, ?) ON CONFLICT (guild_id, user_id) DO UPDATE SET "
            "channel_id = excluded.channel_id, message_id = excluded.message_id",
            (guild_id, user_id, channel_id, message_id),
        )
        await self.connection.commit()

    async def get_panel(self, guild_id: int, channel_id: int) -> int | None:
        async with self.connection.execute(
            "SELECT message_id FROM introduction_panels "
            "WHERE guild_id = ? AND channel_id = ?",
            (guild_id, channel_id),
        ) as cursor:
            row = await cursor.fetchone()
        return row[0] if row is not None else None

    async def get_panels(self, guild_id: int) -> list[tuple[int, int]]:
        async with self.connection.execute(
            "SELECT channel_id, message_id FROM introduction_panels WHERE guild_id = ?",
            (guild_id,),
        ) as cursor:
            rows = await cursor.fetchall()
        return [(row[0], row[1]) for row in rows]

    async def save_panel(self, guild_id: int, channel_id: int, message_id: int):
        await self.connection.execute(
            "INSERT INTO introduction_panels (guild_id, channel_id, message_id) "
            "VALUES (?, ?, ?) ON CONFLICT (guild_id, channel_id) DO UPDATE SET "
            "message_id = excluded.message_id",
            (guild_id, channel_id, message_id),
        )
        await self.connection.commit()
