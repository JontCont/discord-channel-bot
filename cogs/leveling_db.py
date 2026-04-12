import aiosqlite
import os
from pathlib import Path


class LevelingDB:
    """Async SQLite helper for user XP / leveling data."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._db: aiosqlite.Connection | None = None

    async def init(self):
        """Create DB directory, connect, and ensure tables exist."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(self.db_path)
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id     INTEGER NOT NULL,
                guild_id    INTEGER NOT NULL,
                xp          INTEGER NOT NULL DEFAULT 0,
                level       INTEGER NOT NULL DEFAULT 1,
                last_msg_xp REAL    NOT NULL DEFAULT 0,
                daily_streak INTEGER NOT NULL DEFAULT 0,
                last_daily  TEXT    DEFAULT NULL,
                PRIMARY KEY (user_id, guild_id)
            )
        """)
        await self._db.commit()

    async def close(self):
        if self._db:
            await self._db.close()

    async def get_user(self, user_id: int, guild_id: int) -> dict:
        """Get or create a user record."""
        async with self._db.execute(
            "SELECT xp, level, last_msg_xp, daily_streak, last_daily "
            "FROM users WHERE user_id = ? AND guild_id = ?",
            (user_id, guild_id),
        ) as cur:
            row = await cur.fetchone()

        if row:
            return {
                "xp": row[0],
                "level": row[1],
                "last_msg_xp": row[2],
                "daily_streak": row[3],
                "last_daily": row[4],
            }

        await self._db.execute(
            "INSERT INTO users (user_id, guild_id) VALUES (?, ?)",
            (user_id, guild_id),
        )
        await self._db.commit()
        return {
            "xp": 0,
            "level": 1,
            "last_msg_xp": 0.0,
            "daily_streak": 0,
            "last_daily": None,
        }

    async def add_xp(self, user_id: int, guild_id: int, amount: int) -> dict:
        """Add XP and return updated record."""
        user = await self.get_user(user_id, guild_id)
        new_xp = user["xp"] + amount
        new_level = self.calc_level(new_xp)

        await self._db.execute(
            "UPDATE users SET xp = ?, level = ? "
            "WHERE user_id = ? AND guild_id = ?",
            (new_xp, new_level, user_id, guild_id),
        )
        await self._db.commit()
        return {"xp": new_xp, "level": new_level, "old_level": user["level"]}

    async def set_last_msg_xp(self, user_id: int, guild_id: int, timestamp: float):
        await self._db.execute(
            "UPDATE users SET last_msg_xp = ? WHERE user_id = ? AND guild_id = ?",
            (timestamp, user_id, guild_id),
        )
        await self._db.commit()

    async def do_daily(
        self, user_id: int, guild_id: int, today: str
    ) -> dict | None:
        """Perform daily check-in. Returns None if already claimed today."""
        user = await self.get_user(user_id, guild_id)
        if user["last_daily"] == today:
            return None

        # Calculate streak
        from datetime import datetime, timedelta

        streak = 1
        if user["last_daily"]:
            last = datetime.strptime(user["last_daily"], "%Y-%m-%d").date()
            today_date = datetime.strptime(today, "%Y-%m-%d").date()
            if today_date - last == timedelta(days=1):
                streak = user["daily_streak"] + 1
        # else streak resets to 1

        await self._db.execute(
            "UPDATE users SET daily_streak = ?, last_daily = ? "
            "WHERE user_id = ? AND guild_id = ?",
            (streak, today, user_id, guild_id),
        )
        await self._db.commit()
        return {"streak": streak}

    async def get_leaderboard(
        self, guild_id: int, limit: int = 10
    ) -> list[dict]:
        async with self._db.execute(
            "SELECT user_id, xp, level FROM users "
            "WHERE guild_id = ? ORDER BY xp DESC LIMIT ?",
            (guild_id, limit),
        ) as cur:
            rows = await cur.fetchall()
        return [{"user_id": r[0], "xp": r[1], "level": r[2]} for r in rows]

    async def get_rank(self, user_id: int, guild_id: int) -> int:
        """Return 1-based rank of user in guild."""
        async with self._db.execute(
            "SELECT COUNT(*) FROM users "
            "WHERE guild_id = ? AND xp > (SELECT COALESCE(xp,0) FROM users WHERE user_id = ? AND guild_id = ?)",
            (guild_id, user_id, guild_id),
        ) as cur:
            row = await cur.fetchone()
        return (row[0] if row else 0) + 1

    @staticmethod
    def calc_level(xp: int) -> int:
        """Calculate level from total XP. Formula: xp_needed = 40 * level^1.2"""
        level = 1
        cumulative = 0
        while level < 50:
            needed = int(40 * ((level + 1) ** 1.2))
            if cumulative + needed > xp:
                break
            cumulative += needed
            level += 1
        return level

    @staticmethod
    def xp_for_level(level: int) -> int:
        """Return cumulative XP required to reach a given level."""
        cumulative = 0
        for lv in range(2, level + 1):
            cumulative += int(40 * (lv ** 1.2))
        return cumulative

    @staticmethod
    def xp_to_next(xp: int, current_level: int) -> tuple[int, int]:
        """Return (xp_into_current_level, xp_needed_for_next_level)."""
        if current_level >= 50:
            return 0, 0
        current_base = LevelingDB.xp_for_level(current_level)
        next_base = LevelingDB.xp_for_level(current_level + 1)
        return xp - current_base, next_base - current_base
