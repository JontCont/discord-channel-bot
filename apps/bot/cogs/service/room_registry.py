import discord


class RoomRegistry:
    """Shared state for auto-created voice channels (public & private)."""

    def __init__(self):
        # channel_id -> {"owner": user_id, "private": bool, "password": str|None}
        self.active_channels: dict[int, dict] = {}

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

    def unregister(self, channel_id: int):
        self.active_channels.pop(channel_id, None)

    def get(self, channel_id: int) -> dict | None:
        return self.active_channels.get(channel_id)

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
