import json
import unittest

import config
from cogs.repository.guild_settings_db import GuildSettingsDB
from cogs.service.guild_settings_service import GuildSettings, GuildSettingsService


class GuildSettingsServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = GuildSettingsDB(":memory:")
        await self.db.init()
        self.service = GuildSettingsService(self.db)

    async def asyncTearDown(self):
        await self.db.close()

    async def test_get_returns_config_defaults_and_serializable_model(self):
        settings = await self.service.get(1)

        self.assertIsInstance(settings, GuildSettings)
        self.assertEqual(settings.auto_voice_trigger, config.AUTO_VOICE_TRIGGER)
        self.assertEqual(settings.auto_voice_limit, config.AUTO_VOICE_LIMIT)
        self.assertEqual(settings.private_trigger, config.PRIVATE_TRIGGER)
        self.assertEqual(settings.private_limit, config.PRIVATE_LIMIT)
        self.assertEqual(settings.skill_prefix, config.SKILL_PREFIX)
        self.assertEqual(
            settings.skill_panel_direct_join_skills,
            tuple(config.SKILL_PANEL_DIRECT_JOIN_SKILLS),
        )
        self.assertEqual(settings.party_category, "湯技：遊戲術 🎮")
        self.assertEqual(settings.xp_per_message_min, config.XP_PER_MESSAGE_MIN)
        self.assertEqual(settings.level_roles, tuple(config.LEVEL_ROLES))
        self.assertIsInstance(json.dumps(settings.to_dict()), str)

    async def test_update_persists_overrides(self):
        updated = await self.service.update(
            10,
            {
                "auto_voice_limit": 12,
                "private_category": "Members Only",
                "skill_panel_direct_join_skills": ["Cooking", "Music"],
                "party_category": "Gaming",
                "level_roles": [[1, "Newcomer", 0x123456], [5, "Regular", 0]],
            },
        )

        reloaded = await GuildSettingsService(self.db).get(10)
        self.assertEqual(reloaded, updated)
        self.assertEqual(reloaded.auto_voice_limit, 12)
        self.assertEqual(reloaded.private_category, "Members Only")
        self.assertEqual(
            reloaded.skill_panel_direct_join_skills, ("Cooking", "Music")
        )
        self.assertEqual(reloaded.party_category, "Gaming")
        self.assertEqual(
            reloaded.level_roles,
            ((1, "Newcomer", 0x123456), (5, "Regular", 0)),
        )

    async def test_partial_update_preserves_defaults_and_previous_overrides(self):
        await self.service.update(
            20, {"auto_voice_suffix": "Room", "xp_per_message_min": 5}
        )

        settings = await self.service.update(20, {"xp_per_message_max": 8})

        self.assertEqual(settings.auto_voice_suffix, "Room")
        self.assertEqual(settings.xp_per_message_min, 5)
        self.assertEqual(settings.xp_per_message_max, 8)
        self.assertEqual(settings.private_limit, config.PRIVATE_LIMIT)

    async def test_legacy_party_skill_is_read_as_party_category(self):
        await self.db.set_many(21, {"party_skill": "遊戲術"})

        settings = await self.service.get(21)

        self.assertEqual(settings.party_category, "湯技：遊戲術 🎮")

    async def test_rejects_invalid_updates_without_persisting_them(self):
        invalid_changes = {
            "unknown key": {"does_not_exist": 1},
            "boolean integer": {"auto_voice_limit": True},
            "negative voice limit": {"private_limit": -1},
            "excessive voice limit": {"auto_voice_limit": 100},
            "zero interval": {"xp_voice_interval": 0},
            "inverted xp range": {
                "xp_per_message_min": 30,
                "xp_per_message_max": 20,
            },
            "duplicate triggers": {
                "auto_voice_trigger": "Create Room",
                "private_trigger": " create room ",
            },
            "empty required name": {"private_category": "   "},
            "duplicate skill name": {
                "skill_panel_direct_join_skills": ["Music", "Music"]
            },
            "empty skill name": {
                "skill_panel_direct_join_skills": ["Music", ""]
            },
            "malformed role shape": {"level_roles": [[1, "Member"]]},
            "empty roles": {"level_roles": []},
            "boolean role level": {"level_roles": [[True, "Member", 0]]},
            "invalid role color": {"level_roles": [[1, "Member", 0x1000000]]},
            "empty role name": {"level_roles": [[1, " ", 0]]},
            "duplicate role level": {
                "level_roles": [[1, "Member", 0], [1, "Regular", 1]]
            },
            "duplicate role name": {
                "level_roles": [[1, "Member", 0], [2, "Member", 1]]
            },
            "unordered roles": {
                "level_roles": [[2, "Regular", 1], [1, "Member", 0]]
            },
        }

        for label, changes in invalid_changes.items():
            with self.subTest(label=label), self.assertRaises(ValueError):
                await self.service.update(30, changes)

        self.assertEqual(await self.db.get_all(30), {})


if __name__ == "__main__":
    unittest.main()