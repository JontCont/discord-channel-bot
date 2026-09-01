import unittest
from types import SimpleNamespace

from cogs.slash.party import _category_matches


class PartyAccessTests(unittest.TestCase):
    def test_channel_matches_configured_category_case_insensitively(self):
        channel = SimpleNamespace(category=SimpleNamespace(name="遊戲術"))

        self.assertTrue(_category_matches(channel, " 遊戲術 "))
        self.assertFalse(_category_matches(channel, "墨繪術"))


if __name__ == "__main__":
    unittest.main()