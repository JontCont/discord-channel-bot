import asyncio
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import discord

from repository.introduction_db import IntroductionDB
from cogs.slash.introduction import Introduction, IntroductionModal


class IntroductionTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = str(Path(self.directory.name) / "settings.db")
        self.bot = Mock()
        self.cog = Introduction(self.bot)
        self.cog.db = IntroductionDB(self.path)
        await self.cog.cog_load()
        self.channel = Mock(spec=discord.TextChannel)
        self.channel.id = 20
        self.channel.send = AsyncMock()
        self.channel.fetch_message = AsyncMock()
        self.message = Mock(spec=discord.Message)
        self.message.id = 30
        self.message.edit = AsyncMock()
        self.message.pinned = False
        self.message.pin = AsyncMock()
        self.message.jump_url = "https://discord.com/channels/10/20/30"
        self.channel.send.return_value = self.message
        self.channel.fetch_message.return_value = self.message
        self.guild = Mock(spec=discord.Guild)
        self.guild.id = 10
        self.guild.get_channel.return_value = self.channel
        self.guild.fetch_channel = AsyncMock()
        self.interaction = SimpleNamespace(
            guild=self.guild,
            guild_id=10,
            channel=self.channel,
            user=SimpleNamespace(
                id=40,
                mention="<@40>",
                display_name="Member",
                display_avatar=SimpleNamespace(url="https://example.com/avatar.png"),
            ),
            response=SimpleNamespace(
                defer=AsyncMock(),
                send_message=AsyncMock(),
                send_modal=AsyncMock(),
                is_done=Mock(return_value=True),
            ),
            followup=SimpleNamespace(send=AsyncMock()),
        )
        await self.cog.db.save_panel(10, 20, 50)

    async def asyncTearDown(self):
        await self.cog.cog_unload()

    async def test_publish_then_update_after_restart_keeps_one_message(self):
        await self.cog.publish(self.interaction, discord.Embed(title="First"))
        self.channel.send.assert_awaited_once()
        self.assertEqual(await self.cog.db.get(10, 40), (20, 30))
        mentions = self.channel.send.call_args.kwargs["allowed_mentions"]
        self.assertFalse(mentions.everyone)
        self.assertFalse(mentions.roles)
        self.assertFalse(mentions.users)

        await self.cog.cog_unload()
        self.cog = Introduction(self.bot)
        self.cog.db = IntroductionDB(self.path)
        await self.cog.cog_load()
        updated = discord.Embed(title="Updated")
        await self.cog.publish(self.interaction, updated)

        self.channel.send.assert_awaited_once()
        self.channel.fetch_message.assert_awaited_once_with(30)
        self.message.edit.assert_awaited_once()
        self.assertIs(self.message.edit.call_args.kwargs["embed"], updated)
        self.assertTrue(self.cog.view.is_persistent())
        self.bot.add_view.assert_called_with(self.cog.view)

    async def test_concurrent_submissions_create_only_one_introduction(self):
        await asyncio.gather(
            self.cog.publish(self.interaction, discord.Embed(title="First")),
            self.cog.publish(self.interaction, discord.Embed(title="Second")),
        )
        self.channel.send.assert_awaited_once()
        self.message.edit.assert_awaited_once()

    async def test_ready_pins_existing_panel_without_deleting_messages(self):
        self.bot.guilds = [self.guild]
        await self.cog.on_ready()
        self.channel.fetch_message.assert_awaited_once_with(50)
        self.message.pin.assert_awaited_once()
        self.channel.send.assert_not_awaited()
        self.message.delete.assert_not_called()

        self.message.pinned = True
        await self.cog.on_ready()
        self.message.pin.assert_awaited_once()

    async def test_pin_failure_is_logged_without_posting_replacement(self):
        self.bot.guilds = [self.guild]
        self.message.pin.side_effect = discord.Forbidden(
            Mock(status=403, reason="Forbidden"), "missing pin permission"
        )
        with self.assertLogs("cogs.slash.introduction", level="WARNING"):
            await self.cog.on_ready()
        self.channel.send.assert_not_awaited()

    async def test_deleted_message_is_recreated_but_forbidden_is_not(self):
        await self.cog.db.save(10, 40, 20, 99)
        response = Mock(status=404, reason="Not Found")
        self.channel.fetch_message.side_effect = discord.NotFound(response, "deleted")
        await self.cog.publish(self.interaction, discord.Embed())
        self.assertEqual(await self.cog.db.get(10, 40), (20, 30))

        self.channel.send.reset_mock()
        response = Mock(status=403, reason="Forbidden")
        self.channel.fetch_message.side_effect = discord.Forbidden(response, "denied")
        with self.assertRaises(discord.Forbidden):
            await self.cog.publish(self.interaction, discord.Embed())
        self.channel.send.assert_not_awaited()

    async def test_missing_cached_channel_is_fetched_before_updating(self):
        await self.cog.db.save(10, 40, 20, 30)
        self.guild.get_channel.return_value = None
        self.guild.fetch_channel.return_value = self.channel
        await self.cog.publish(self.interaction, discord.Embed())
        self.guild.fetch_channel.assert_awaited_once_with(20)
        self.message.edit.assert_awaited_once()
        self.channel.send.assert_not_awaited()

    async def test_introductions_are_scoped_to_guild_and_member(self):
        await self.cog.db.save(10, 40, 20, 30)
        await self.cog.db.save(11, 40, 21, 31)
        await self.cog.db.save(10, 41, 20, 32)
        await self.cog.db.save(10, 40, 20, 33)
        self.assertEqual(await self.cog.db.get(10, 40), (20, 33))
        self.assertEqual(await self.cog.db.get(11, 40), (21, 31))
        self.assertEqual(await self.cog.db.get(10, 41), (20, 32))

    async def test_setup_creates_channel_and_reuses_panel_on_repeat(self):
        category = Mock(spec=discord.CategoryChannel)
        category.text_channels = []
        category.create_text_channel = AsyncMock(return_value=self.channel)
        await self.cog.db.save_panel(10, 20, 50)
        self.channel.fetch_message.side_effect = discord.NotFound(
            Mock(status=404, reason="Not Found"), "deleted"
        )
        await Introduction.setup_introduction.callback(
            self.cog, self.interaction, category
        )
        category.create_text_channel.assert_awaited_once()
        self.channel.send.assert_awaited_once()
        self.message.pin.assert_awaited_once()
        self.assertEqual(await self.cog.db.get_panel(10, 20), 30)

        category.text_channels = [self.channel]
        self.channel.name = category.create_text_channel.call_args.args[0]
        self.channel.fetch_message.side_effect = None
        self.message.pinned = True
        await Introduction.setup_introduction.callback(
            self.cog, self.interaction, category
        )
        category.create_text_channel.assert_awaited_once()
        self.channel.send.assert_awaited_once()
        self.message.edit.assert_awaited_once()
        self.message.pin.assert_awaited_once()

    async def test_button_opens_modal(self):
        await self.cog.view.children[0].callback(self.interaction)
        modal = self.interaction.response.send_modal.call_args.args[0]
        self.assertIsInstance(modal, IntroductionModal)
        self.assertIs(modal.cog, self.cog)

    async def test_modal_submission_works_with_voice_operations_disabled(self):
        modal = IntroductionModal(self.cog)
        for field, value in (
            (modal.nickname, "Nickname"),
            (modal.interests, "Games"),
            (modal.looking_for, ""),
            (modal.availability, "Evenings"),
        ):
            field._value = value
        with (
            patch("config.DYNAMIC_VOICE_CREATE_ENABLED", False),
            patch("config.DYNAMIC_VOICE_DELETE_ENABLED", False),
        ):
            await modal.on_submit(self.interaction)
        self.interaction.response.defer.assert_awaited_once_with(ephemeral=True)
        self.channel.send.assert_awaited_once()
        embed = self.channel.send.call_args.kwargs["embed"]
        self.assertEqual(
            [field.value for field in embed.fields],
            ["Nickname", "Games", "未填寫", "Evenings"],
        )
        self.interaction.followup.send.assert_awaited_once()

    async def test_blank_required_fields_do_not_publish(self):
        modal = IntroductionModal(self.cog)
        modal.nickname._value = "   "
        modal.interests._value = "Games"
        await modal.on_submit(self.interaction)
        self.interaction.response.send_message.assert_awaited_once()
        self.channel.send.assert_not_awaited()

    async def test_modal_errors_are_logged_and_reported(self):
        modal = IntroductionModal(self.cog)
        with self.assertLogs("cogs.slash.introduction", level="ERROR"):
            await modal.on_error(self.interaction, RuntimeError("test failure"))
        self.interaction.followup.send.assert_awaited_once()
        self.assertTrue(self.interaction.followup.send.call_args.kwargs["ephemeral"])
