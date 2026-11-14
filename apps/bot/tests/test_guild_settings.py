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
        self.assertTrue(settings.auto_voice_enabled)
        self.assertTrue(settings.private_rooms_enabled)
        self.assertTrue(settings.skills_enabled)
        self.assertTrue(settings.party_enabled)
        self.assertTrue(settings.leveling_enabled)
        self.assertEqual(settings.auto_voice_limit, config.AUTO_VOICE_LIMIT)
        self.assertEqual(settings.private_trigger, config.PRIVATE_TRIGGER)
        self.assertEqual(settings.private_limit, config.PRIVATE_LIMIT)
        self.assertEqual(settings.skill_prefix, config.SKILL_PREFIX)
        self.assertEqual(
            settings.skill_panel_direct_join_skills,
            tuple(config.SKILL_PANEL_DIRECT_JOIN_SKILLS),
        )
        self.assertEqual(settings.xp_per_message_min, config.XP_PER_MESSAGE_MIN)
        self.assertEqual(settings.level_roles, tuple(config.LEVEL_ROLES))
        self.assertIsInstance(json.dumps(settings.to_dict()), str)

    async def test_update_persists_overrides(self):
        updated = await self.service.update(
            10,
            {
                "auto_voice_enabled": False,
                "auto_voice_limit": 12,
                "private_category": "Members Only",
                "party_enabled": False,
                "skill_panel_direct_join_skills": ["Cooking", "Music"],
                "level_roles": [[1, "Newcomer", 0x123456], [5, "Regular", 0]],
            },
        )

        reloaded = await GuildSettingsService(self.db).get(10)
        self.assertEqual(reloaded, updated)
        self.assertFalse(reloaded.auto_voice_enabled)
        self.assertFalse(reloaded.party_enabled)
        self.assertEqual(reloaded.auto_voice_limit, 12)
        self.assertEqual(reloaded.private_category, "Members Only")
        self.assertEqual(
            reloaded.skill_panel_direct_join_skills, ("Cooking", "Music")
        )
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

    async def test_panel_text_is_persisted_per_guild_and_footer_can_be_hidden(self):
        await self.service.update(40, {
            "party_panel_title": "Community lobby",
            "party_panel_description": "Choose a room.\n**Welcome!**",
            "party_panel_create_label": "New room",
            "skill_panel_title": "Choose interests",
            "skill_panel_footer": "",
        })
        saved = await GuildSettingsService(self.db).get(40)
        self.assertEqual(saved.party_panel_title, "Community lobby")
        self.assertEqual(saved.party_panel_description, "Choose a room.\n**Welcome!**")
        self.assertEqual(saved.party_panel_create_label, "New room")
        self.assertEqual(saved.skill_panel_title, "Choose interests")
        self.assertEqual(saved.skill_panel_footer, "")
        self.assertEqual((await self.service.get(41)).party_panel_title, GuildSettings().party_panel_title)

    async def test_panel_text_limits_match_discord_and_reject_without_persisting(self):
        await self.service.update(50, {"party_panel_title": "x" * 256, "party_panel_create_label": "x" * 80})
        for changes in (
            {"party_panel_title": "x" * 257},
            {"party_panel_create_label": "x" * 81},
            {"skill_panel_description": "x" * 4097},
            {"skill_panel_footer": "x" * 2049},
            {"party_panel_list_description": "   "},
            {"skill_panel_footer": None},
            {"party_panel_description": "x" * 4096,
             "party_panel_create_description": "x" * 1024,
             "party_panel_list_description": "x" * 1024},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                await self.service.update(51, changes)
        self.assertEqual(await self.db.get_all(51), {})

    async def test_legacy_party_keys_are_ignored(self):
        await self.db.set_many(21, {"party_skill": "遊戲術", "party_category": "遊戲術"})

        settings = await self.service.get(21)
        self.assertNotIn("party_category", settings.to_dict())

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