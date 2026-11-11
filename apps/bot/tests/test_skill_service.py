import unittest
from unittest.mock import Mock

import discord
from cogs.repository.skill_invite_repository import SkillInviteRepository
from cogs.service.skill_service import SkillService
from cogs.service.guild_settings_service import GuildSettings


class SkillServiceTests(unittest.TestCase):
    def test_custom_panel_copy_preserves_dynamic_skill_counts_and_optional_footer(self):
        service = SkillService(repo=Mock(spec=SkillInviteRepository))
        guild = Mock(spec=discord.Guild)
        guild.roles = []
        embed = service.build_panel_embed(
            [("Music", None)], guild, "Skill:", ("Music",),
            settings=GuildSettings(
                skill_panel_title="Interests",
                skill_panel_description="**Join us!**",
                skill_panel_footer="",
            ),
        )
        self.assertEqual(embed.title, "Interests")
        self.assertTrue(embed.description.startswith("**Join us!**"))
        self.assertIn("Music", embed.description)
        self.assertIn("0 位成員", embed.description)
        self.assertIsNone(embed.footer.text)

    def test_panel_explains_purpose_access_and_toggle_behavior(self):
        service = SkillService(repo=Mock(spec=SkillInviteRepository))
        guild = Mock(spec=discord.Guild)
        guild.roles = []
        embed = service.build_panel_embed(
            [("遊戲術", "🎮")], guild, "湯技：", ("遊戲術",)
        )
        self.assertIn("興趣分組", embed.description)
        self.assertIn("身分組", embed.description)
        self.assertIn("聊天、討論與語音頻道", embed.description)
        self.assertIn("可以同時加入多個", embed.description)
        self.assertIn("再點一次就會離開", embed.description)
        self.assertIn("遊戲術", embed.description)
        self.assertIn("/skill join", embed.footer.text)

    def test_filter_panel_skills_only_includes_configured_names_in_config_order(self):
        skills = [
            ("教學術", None),
            ("遊戲術", "🎮"),
            ("鍛造術", "🔧"),
            ("NAS", None),
        ]

        filtered = SkillService.filter_panel_skills(
            skills,
            ("鍛造術", "遊戲術", "不存在", "nas"),
        )

        self.assertEqual(
            filtered,
            [("鍛造術", "🔧"), ("遊戲術", "🎮"), ("NAS", None)],
        )

    def test_filter_panel_skills_empty_configuration_hides_all_skills(self):
        filtered = SkillService.filter_panel_skills(
            [("遊戲術", "🎮")],
            (),
        )

        self.assertEqual(filtered, [])


if __name__ == "__main__":
    unittest.main()