"""
Guild Settings Domain Model.

官方依據: PEP 557 (Data Classes).
純粹的資料容器模型，使用 @dataclass(frozen=True, slots=True) 保證不可變性與低記憶體開銷。
不混入任何驗證邏輯與資料庫存取。
"""
from dataclasses import asdict, dataclass
from typing import Any

import config


@dataclass(frozen=True, slots=True)
class GuildSettings:
    """伺服器設定實體 (Domain Model)."""

    auto_voice_enabled: bool = True
    auto_voice_trigger: str = config.AUTO_VOICE_TRIGGER
    auto_voice_suffix: str = config.AUTO_VOICE_SUFFIX
    auto_voice_limit: int = config.AUTO_VOICE_LIMIT

    private_rooms_enabled: bool = True
    private_category: str = config.PRIVATE_CATEGORY
    private_trigger: str = config.PRIVATE_TRIGGER
    private_suffix: str = config.PRIVATE_SUFFIX
    private_limit: int = config.PRIVATE_LIMIT
    password_channel: str = config.PASSWORD_CHANNEL

    skills_enabled: bool = True
    skill_prefix: str = config.SKILL_PREFIX
    skill_panel_channel: str = config.SKILL_PANEL_CHANNEL
    skill_panel_direct_join_skills: tuple[str, ...] = tuple(
        config.SKILL_PANEL_DIRECT_JOIN_SKILLS
    )

    party_enabled: bool = True
    party_notification_channel: str = config.PARTY_NOTIFICATION_CHANNEL
    party_panel_title: str = "🏠 房間大廳"
    party_panel_description: str = (
        "想聊天、玩遊戲或找同好？選擇分類就能建立公開語音房，不必先加入遊戲湯技。\n"
        "表單填寫房名、人數、備註，並可多選自己已加入的湯技作為通知身分。\n"
        "送出表單後，Bot 會自動在揪團通知頻道公告，並標記你選的湯技身分。\n"
        "所有人離開後自動清理房間。"
    )
    party_panel_create_heading: str = "建立房間"
    party_panel_create_description: str = "選擇建立分類，填寫房名、人數、備註與通知身分（可多選）。"
    party_panel_list_heading: str = "查看房間"
    party_panel_list_description: str = "先加入任一語音頻道，再從即時列表選擇揪團，Bot 會直接移動你。"
    party_panel_create_label: str = "建立房間"
    party_panel_list_label: str = "查看房間"
    skill_panel_title: str = "🎯 選擇你的湯技"
    skill_panel_description: str = (
        "「湯技」就是這裡的**興趣分組**，幫你找到有共同興趣的同好。\n"
        "加入後會取得對應身分組，並看見該分組的聊天、討論與語音頻道。\n\n"
        "**怎麼加入？**\n"
        "選擇感興趣的湯技，點下方按鈕即可加入，**可以同時加入多個**。\n"
        "已加入的湯技再點一次就會離開，並收起對應的專屬頻道。"
    )
    skill_panel_footer: str = "💡 其餘湯技需向邀請人取得邀請碼，再使用 /skill join 加入。"

    leveling_enabled: bool = True
    xp_per_message_min: int = config.XP_PER_MESSAGE_MIN
    xp_per_message_max: int = config.XP_PER_MESSAGE_MAX
    xp_message_cooldown: int = config.XP_MESSAGE_COOLDOWN
    xp_per_voice_tick: int = config.XP_PER_VOICE_TICK
    xp_voice_interval: int = config.XP_VOICE_INTERVAL
    xp_daily_base: int = config.XP_DAILY_BASE
    levelup_channel: str = config.LEVELUP_CHANNEL
    level_roles: tuple[tuple[int, str, int], ...] = tuple(config.LEVEL_ROLES)

    def to_dict(self) -> dict[str, Any]:
        """序列化為可直接 JSON 輸出的原生字典。"""
        data = asdict(self)
        data["skill_panel_direct_join_skills"] = list(
            self.skill_panel_direct_join_skills
        )
        data["level_roles"] = [list(role) for role in self.level_roles]
        return data
