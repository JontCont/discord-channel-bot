"""
Core Enums (Domain Enums).

官方依據: PEP 435 (Enum) & Python 3.11+ enum.StrEnum.
定義領域枚舉型別，直接繼承 StrEnum，免除手動 .value 轉換並提供靜態型別約束。
"""
from enum import StrEnum


class FeatureModule(StrEnum):
    """5 大功能模組識別代碼。"""
    AUTO_VOICE = "auto_voice"
    PRIVATE_ROOMS = "private_rooms"
    SKILLS = "skills"
    PARTY = "party"
    LEVELING = "leveling"


class VoiceRoomType(StrEnum):
    """動態建立之語音房間類型。"""
    AUTO = "auto"
    PRIVATE = "private"
    PARTY = "party"
