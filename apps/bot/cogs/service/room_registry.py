import json
import logging
from pathlib import Path

import discord


logger = logging.getLogger(__name__)


class RoomRegistry:
    """Shared state for auto-created voice channels (public & private)."""

    def __init__(self, path: str | Path = "data/room_registry.json"):
        # channel_id -> {"owner": user_id, "private": bool, "password": str|None}
        self.active_channels: dict[int, dict] = {}
        self._path = Path(path)
        self._load()

    def register(
        self,
        channel_id: int,
        owner_id: int,
        *,
        private: bool = False,
        password: str | None = None,
    ):
        self.active_channels[channel_id] = {
            "owner": owner_id,
            "private": private,
            "password": password,
        }
        self._save()

    def unregister(self, channel_id: int):
        if self.active_channels.pop(channel_id, None) is not None:
            self._save()

    def get(self, channel_id: int) -> dict | None:
        return self.active_channels.get(channel_id)

    def entries(self) -> tuple[tuple[int, dict], ...]:
        return tuple(self.active_channels.items())

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            payload = json.loads(self._path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("registry root must be an object")
            for channel_id, info in payload.items():
                if not isinstance(info, dict) or not isinstance(info.get("owner"), int):
                    continue
                self.active_channels[int(channel_id)] = {
                    "owner": info["owner"],
                    "private": bool(info.get("private", False)),
                    "password": info.get("password"),
                }
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            logger.exception("Failed to load room registry from %s", self._path)

    def _save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            temporary_path = self._path.with_suffix(f"{self._path.suffix}.tmp")
            temporary_path.write_text(
                json.dumps(self.active_channels, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            temporary_path.replace(self._path)
        except OSError:
            logger.exception("Failed to save room registry to %s", self._path)

    def get_owned_channel(
        self, interaction: discord.Interaction
    ) -> tuple[discord.VoiceChannel | None, str | None]:
        """Return (channel, error_message). error_message is None on success."""
        if interaction.user.voice is None or interaction.user.voice.channel is None:
            return None, "❌ 你必須先在語音頻道中才能使用此指令。"

        channel = interaction.user.voice.channel
        info = self.active_channels.get(channel.id)
        if info is None:
            return None, "❌ 這不是自動建立的語音頻道。"
        if info["owner"] != interaction.user.id:
            return None, "❌ 只有房主才能使用此指令。"
        return channel, None

    def find_by_password(self, password: str) -> tuple[int | None, dict | None]:
        """Find a private room matching the given password."""
        for channel_id, info in self.active_channels.items():
            if info["private"] and info["password"] == password:
                return channel_id, info
        return None, None
