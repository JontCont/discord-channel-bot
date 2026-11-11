import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import config
from cogs.slash.auto_voice import AutoVoice
from cogs.slash.party import PartyCreateModal
from cogs.slash.private_room import PrivateRoom


class DynamicVoiceControlsTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.settings = SimpleNamespace(
            auto_voice_trigger="Create public",
            auto_voice_suffix="room",
            auto_voice_limit=6,
            private_trigger="Create private",
            private_suffix="private",
            private_limit=4,
            level_roles=(),
            password_channel="passwords",
        )
        self.bot = SimpleNamespace(
            guild_settings_service=SimpleNamespace(
                get=AsyncMock(return_value=self.settings)
            ),
            room_registry=Mock(),
            get_channel=Mock(),
            guilds=[],
        )
        self.auto = AutoVoice.__new__(AutoVoice)
        self.auto.bot = self.bot
        self.member = Mock()
        self.member.display_name = "Member"
        self.member.guild.create_voice_channel = AsyncMock()
        self.member.move_to = AsyncMock()
        self.member.send = AsyncMock()

    async def test_creation_switch_blocks_public_and_private_triggers(self):
        for enabled in (False, True):
            for cog, trigger in (
                (self.auto, self.settings.auto_voice_trigger),
                (PrivateRoom(self.bot), self.settings.private_trigger),
            ):
                with self.subTest(enabled=enabled, trigger=trigger):
                    self.member.guild.create_voice_channel.reset_mock()
                    self.member.move_to.reset_mock()
                    before = SimpleNamespace(channel=None)
                    after = SimpleNamespace(
                        channel=SimpleNamespace(name=trigger, category=Mock())
                    )
                    with patch.object(config, "DYNAMIC_VOICE_CREATE_ENABLED", enabled):
                        await cog.on_voice_state_update(self.member, before, after)
                    self.assertEqual(
                        self.member.guild.create_voice_channel.await_count, int(enabled)
                    )
                    self.assertEqual(self.member.move_to.await_count, int(enabled))

    async def test_disabled_party_submission_notifies_without_side_effects(self):
        modal = PartyCreateModal(
            self.bot, [SimpleNamespace(id=1, name="General")], []
        )
        interaction = SimpleNamespace(
            response=SimpleNamespace(send_message=AsyncMock())
        )
        with patch.object(config, "DYNAMIC_VOICE_CREATE_ENABLED", False):
            await modal.on_submit(interaction)
        interaction.response.send_message.assert_awaited_once()
        self.assertTrue(interaction.response.send_message.call_args.kwargs["ephemeral"])
        self.bot.guild_settings_service.get.assert_not_awaited()
        self.bot.room_registry.register.assert_not_called()

    async def test_delete_switch_controls_empty_room_event_independently(self):
        for enabled in (False, True):
            with self.subTest(enabled=enabled):
                channel = SimpleNamespace(id=123, members=[], delete=AsyncMock())
                self.bot.room_registry.unregister.reset_mock()
                with (
                    patch.object(config, "DYNAMIC_VOICE_CREATE_ENABLED", False),
                    patch.object(config, "DYNAMIC_VOICE_DELETE_ENABLED", enabled),
                ):
                    await self.auto.on_voice_state_update(
                        self.member,
                        SimpleNamespace(channel=channel),
                        SimpleNamespace(channel=None),
                    )
                self.assertEqual(channel.delete.await_count, int(enabled))
                self.assertEqual(
                    self.bot.room_registry.unregister.call_count, int(enabled)
                )

    async def test_disabled_delete_helper_preserves_room_and_registration(self):
        channel = SimpleNamespace(id=123, members=[], delete=AsyncMock())
        with patch.object(config, "DYNAMIC_VOICE_DELETE_ENABLED", False):
            deleted = await self.auto._delete_registered_channel(channel, reason="test")
        self.assertFalse(deleted)
        channel.delete.assert_not_awaited()
        self.bot.room_registry.unregister.assert_not_called()

    async def test_disabled_periodic_cleanup_skips_registered_and_orphan_scans(self):
        with patch.object(config, "DYNAMIC_VOICE_DELETE_ENABLED", False):
            await AutoVoice.cleanup_empty_rooms.coro(self.auto)
        self.bot.room_registry.entries.assert_not_called()
        self.bot.room_registry.unregister.assert_not_called()
        self.bot.get_channel.assert_not_called()
        self.bot.guild_settings_service.get.assert_not_awaited()

    async def test_enabled_deletion_still_preserves_occupied_rooms(self):
        channel = SimpleNamespace(id=123, members=[self.member], delete=AsyncMock())
        with patch.object(config, "DYNAMIC_VOICE_DELETE_ENABLED", True):
            deleted = await self.auto._delete_registered_channel(channel, reason="test")
        self.assertFalse(deleted)
        channel.delete.assert_not_awaited()
        self.bot.room_registry.unregister.assert_not_called()


class DynamicVoiceConfigTests(unittest.TestCase):
    def test_boolean_flags_default_parse_and_reject_invalid_values(self):
        key = "DYNAMIC_VOICE_CREATE_ENABLED"
        with patch.dict(os.environ, {}, clear=True):
            self.assertTrue(config._get_bool_env(key, True))
        for value, expected in (("true", True), ("false", False), (" FALSE ", False)):
            with self.subTest(value=value), patch.dict(os.environ, {key: value}):
                self.assertEqual(config._get_bool_env(key, True), expected)
        with patch.dict(os.environ, {key: "flase"}):
            with self.assertRaisesRegex(ValueError, key):
                config._get_bool_env(key, True)
