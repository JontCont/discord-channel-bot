import unittest

from cogs.service.skill_service import SkillService


class SkillServiceTests(unittest.TestCase):
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