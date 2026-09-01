import tempfile
import unittest
from pathlib import Path

from cogs.service.room_registry import RoomRegistry


class RoomRegistryTests(unittest.TestCase):
    def test_registry_survives_restart_and_unregister(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rooms.json"
            registry = RoomRegistry(path)
            registry.register(101, 201)
            registry.register(102, 202, private=True, password="ABC123")

            reloaded = RoomRegistry(path)

            self.assertEqual(reloaded.get(101), {
                "owner": 201,
                "private": False,
                "password": None,
            })
            self.assertEqual(reloaded.get(102), {
                "owner": 202,
                "private": True,
                "password": "ABC123",
            })

            reloaded.unregister(101)

            after_unregister = RoomRegistry(path)
            self.assertIsNone(after_unregister.get(101))
            self.assertIsNotNone(after_unregister.get(102))

    def test_entries_are_a_stable_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            registry = RoomRegistry(Path(directory) / "rooms.json")
            registry.register(101, 201)

            entries = registry.entries()
            registry.unregister(101)

            self.assertEqual(entries, ((101, {
                "owner": 201,
                "private": False,
                "password": None,
            }),))

    def test_invalid_registry_file_starts_empty(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rooms.json"
            path.write_text("not-json", encoding="utf-8")

            with self.assertLogs("cogs.service.room_registry", level="ERROR"):
                registry = RoomRegistry(path)

            self.assertEqual(registry.entries(), ())


if __name__ == "__main__":
    unittest.main()