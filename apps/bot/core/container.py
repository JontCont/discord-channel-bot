"""
Service Container (Dependency Injection & Composition Root).

官方依據: Clean Architecture (Robert C. Martin) 第 5 部分.
集中組裝 Repository、Service 與全域狀態，管控系統生命週期。
"""
from dataclasses import dataclass
from pathlib import Path

import config
from repository.guild_settings_db import GuildSettingsDB
from repository.introduction_db import IntroductionDB
from repository.leveling_db import LevelingDB
from repository.skill_invite_repository import SkillInviteRepository
from service.guild_settings_service import GuildSettingsService
from service.room_registry import RoomRegistry
from service.skill_service import SkillService


@dataclass
class ServiceContainer:
    """依賴注入容器：管理全域 Service 與 Repository 單例實體。"""

    # Repositories (DAL)
    guild_settings_db: GuildSettingsDB
    leveling_db: LevelingDB
    introduction_db: IntroductionDB
    skill_invite_repo: SkillInviteRepository

    # Services (Application Layer)
    guild_settings_service: GuildSettingsService
    skill_service: SkillService
    room_registry: RoomRegistry

    @classmethod
    def create(
        cls,
        settings_db_path: str = config.SETTINGS_DB_PATH,
        leveling_db_path: str = config.LEVELING_DB_PATH,
        introduction_db_path: str = "data/introductions.db",
        skill_invite_db_path: str = "data/skill_invites.db",
        room_registry_path: str = "data/room_registry.json",
    ) -> "ServiceContainer":
        """工廠方法：建立並裝配所有 Repositories 與 Services。"""
        # 1. 建立 Repositories
        settings_db = GuildSettingsDB(settings_db_path)
        leveling_db = LevelingDB(leveling_db_path)
        intro_db = IntroductionDB(introduction_db_path)
        skill_repo = SkillInviteRepository(skill_invite_db_path)

        # 2. 建立 Services (注入相依之 Repository)
        settings_service = GuildSettingsService(settings_db)
        skill_svc = SkillService(skill_repo)
        rooms = RoomRegistry(room_registry_path)

        return cls(
            guild_settings_db=settings_db,
            leveling_db=leveling_db,
            introduction_db=intro_db,
            skill_invite_repo=skill_repo,
            guild_settings_service=settings_service,
            skill_service=skill_svc,
            room_registry=rooms,
        )

    async def init(self) -> None:
        """非同步初始化所有持久化連線與表格結構。"""
        await self.guild_settings_db.init()
        await self.leveling_db.init()
        await self.introduction_db.init()
        await self.skill_invite_repo.init()

    async def close(self) -> None:
        """優雅關閉所有資料庫連線並釋放資源。"""
        await self.guild_settings_db.close()
        await self.leveling_db.close()
        await self.introduction_db.close()
        await self.skill_invite_repo.close()
