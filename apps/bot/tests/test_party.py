import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import discord

import config
from cogs.service.panel_service import upsert_panel
from cogs.service.guild_settings_service import GuildSettings
from cogs.slash.party import (
    PartyCommands,
    PartyCreateModal,
    PartyCreatedView,
    PartyJoinConfirmView,
    PartyPanelView,
    _open_party_modal,
    _require_party_access,
    _send_party_list,
)


async def _messages(items):
    for item in items:
        yield item


class CommunityRoomTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.settings = SimpleNamespace(**{
            **GuildSettings().to_dict(),
            "skill_panel_channel": "🎯｜社群入口",
            "party_category": "湯技：遊戲術 🎮",
            "skill_prefix": "湯技：",
            "private_category": "🔒 私人湯",
        })
        self.permissions = SimpleNamespace(
            view_channel=True, connect=True, send_messages=True, embed_links=True,
            manage_channels=True,
        )
        self.guild = Mock(spec=discord.Guild)
        self.guild.id = 10
        self.guild.me = Mock(spec=discord.Member)
        self.guild.default_role = Mock(spec=discord.Role)
        self.skill_role = Mock(spec=discord.Role)
        self.skill_role.id = 100
        self.skill_role.name = "湯技：遊戲術 🎮"
        self.skill_role.mention = "<@&100>"
        self.level_role = Mock(spec=discord.Role)
        self.level_role.id = 101
        self.level_role.name = "Level 5"
        self.guild.roles = [self.guild.default_role, self.skill_role, self.level_role]
        self.category = Mock(spec=discord.CategoryChannel)
        self.category.id = 11
        self.category.name = self.settings.party_category
        self.category.permissions_for.return_value = self.permissions
        self.guild.categories = [self.category]
        self.general = Mock(spec=discord.CategoryChannel)
        self.general.id = 21
        self.general.name = "一般"
        self.general.permissions_for.return_value = self.permissions
        self.activity = Mock(spec=discord.CategoryChannel)
        self.activity.id = 31
        self.activity.name = "活動"
        self.activity.permissions_for.return_value = self.permissions
        self.private = Mock(spec=discord.CategoryChannel)
        self.private.id = 41
        self.private.name = self.settings.private_category
        self.private.permissions_for.return_value = self.permissions
        self.guild.categories = [self.category, self.general, self.activity, self.private]
        self.entry = Mock(spec=discord.TextChannel)
        self.entry.name = self.settings.skill_panel_channel
        self.entry.guild = self.guild
        self.entry.category = self.general
        self.entry.send = AsyncMock()
        self.entry.permissions_for.return_value = self.permissions
        self.notification = Mock(spec=discord.TextChannel)
        self.notification.name = config.PARTY_NOTIFICATION_CHANNEL
        self.notification.guild = self.guild
        self.notification.send = AsyncMock()
        self.notification.permissions_for.return_value = self.permissions
        self.notification.mention = "<#20>"
        self.general.text_channels = [self.entry, self.notification]
        self.general.create_text_channel = AsyncMock(return_value=self.notification)
        self.guild.text_channels = [self.entry, self.notification]
        self.room = Mock(spec=discord.VoiceChannel)
        self.room.guild = self.guild
        self.room.id = 77
        self.room.name = "Room"
        self.room.mention = "<#77>"
        self.room.user_limit = 5
        self.room.members = []
        self.room.permissions_for.return_value = self.permissions
        self.guild.get_channel.return_value = self.room
        self.guild.create_voice_channel = AsyncMock(return_value=self.room)
        self.member = Mock(spec=discord.Member)
        self.member.id = 40
        self.member.guild = self.guild
        self.member.mention = "<@40>"
        self.member.voice = None
        self.member.roles = [self.skill_role, self.level_role]
        self.party = {"game": "Game", "title": "Title", "note": "Note"}
        self.info = {"owner": self.member.id, "party": self.party}
        self.bot = Mock()
        self.bot.guild_settings_service.get = AsyncMock(return_value=self.settings)
        self.bot.room_registry.entries.return_value = ()
        self.bot.room_registry.get.return_value = self.info
        self.interaction = SimpleNamespace(
            guild=self.guild,
            guild_id=10,
            user=self.member,
            channel=self.entry,
            response=SimpleNamespace(
                send_message=AsyncMock(), defer=AsyncMock(), send_modal=AsyncMock()
            ),
            followup=SimpleNamespace(send=AsyncMock()),
            edit_original_response=AsyncMock(),
        )

    def modal(self, roles=None):
        if roles is None:
            roles = [self.skill_role] if self.skill_role in self.member.roles else []
        modal = PartyCreateModal(self.bot, self.guild.categories, roles)
        modal.category_select._values = ["11"]
        for field, value in (
            (modal.room_name, "Room Name"),
            (modal.user_limit, "5"), (modal.note, "Note"),
        ):
            field._value = value
        return modal

    def created_view(self, role_ids=()):
        self.party["notify_role_ids"] = list(role_ids)
        return PartyCreatedView(self.bot, self.room, self.member.id)

    async def test_any_writable_text_channel_can_be_used_without_game_role(self):
        self.entry.name = "general-chat"
        self.member.roles = [self.level_role]
        self.assertTrue(await _require_party_access(self.interaction))
        self.interaction.response.send_message.assert_not_awaited()

    async def test_channel_without_send_permission_cannot_be_used(self):
        self.entry.permissions_for.return_value = SimpleNamespace(
            view_channel=True, send_messages=False
        )
        self.assertFalse(await _require_party_access(self.interaction))
        self.interaction.response.send_message.assert_awaited_once()

    async def test_create_uses_selected_category_and_does_not_send_notification(self):
        modal = self.modal()
        modal.category_select._values = ["31"]
        modal.notify_roles._values = ["100"]
        with patch.object(config, "DYNAMIC_VOICE_CREATE_ENABLED", True):
            await modal.on_submit(self.interaction)
        self.assertIs(
            self.guild.create_voice_channel.call_args.kwargs["category"], self.activity
        )
        self.assertEqual(self.guild.create_voice_channel.call_args.args[0], "Room Name")
        self.bot.room_registry.register.assert_called_once()
        party = self.bot.room_registry.register.call_args.kwargs["party"]
        self.assertEqual(party["title"], "Room Name")
        self.assertEqual(party["notify_role_ids"], [100])
        self.assertNotIn("game", party)
        self.notification.send.assert_not_awaited()
        view = self.interaction.followup.send.call_args.kwargs["view"]
        self.assertIsInstance(view, PartyCreatedView)

    async def test_non_game_member_can_choose_activity_and_create_public_room(self):
        self.member.roles = [self.level_role]
        self.category.permissions_for.side_effect = lambda member: (
            self.permissions if member is self.guild.me
            else SimpleNamespace(view_channel=False, connect=False)
        )
        modal = self.modal()
        modal.category_select._values = ["31"]
        with patch.object(config, "DYNAMIC_VOICE_CREATE_ENABLED", True):
            await modal.on_submit(self.interaction)
        self.guild.create_voice_channel.assert_awaited_once()
        overwrites = self.guild.create_voice_channel.call_args.kwargs["overwrites"]
        overwrite = overwrites[self.guild.default_role]
        self.assertTrue(overwrite.view_channel)
        self.assertTrue(overwrite.connect)
        self.assertEqual(list(overwrites), [self.guild.default_role])
        self.notification.send.assert_not_awaited()
        self.assertEqual(
            self.bot.room_registry.register.call_args.kwargs["party"]["notify_role_ids"], []
        )

    async def test_form_has_exactly_five_fields_with_two_dropdowns_and_multiple_roles(self):
        another_role = Mock(spec=discord.Role)
        another_role.id = 102
        another_role.name = "湯技：墨繪術"
        modal = self.modal([self.skill_role, another_role])
        components = modal.to_dict()["components"]
        self.assertEqual(
            [component["label"] for component in components],
            ["建立分類", "房名", "人數", "備註", "通知身分"],
        )
        self.assertEqual(
            [component["component"]["type"] for component in components], [3, 4, 4, 4, 3]
        )
        notification = components[4]["component"]
        self.assertEqual(notification["max_values"], 2)
        self.assertEqual(notification["min_values"], 0)
        self.assertFalse(notification["required"])
        self.assertEqual(
            [option["value"] for option in notification["options"]], ["100", "102"]
        )

    async def test_modal_open_only_lists_visible_categories_bot_can_manage(self):
        hidden = Mock(spec=discord.CategoryChannel)
        hidden.name = "Hidden"
        hidden.id = 22
        hidden.permissions_for.side_effect = lambda member: (
            self.permissions if member is self.guild.me
            else SimpleNamespace(view_channel=False)
        )
        no_bot_permission = Mock(spec=discord.CategoryChannel)
        no_bot_permission.name = "No bot permission"
        no_bot_permission.id = 23
        no_bot_permission.permissions_for.side_effect = lambda member: (
            SimpleNamespace(view_channel=True, manage_channels=False)
            if member is self.guild.me else self.permissions
        )
        self.guild.categories.extend([hidden, no_bot_permission])
        await _open_party_modal(self.bot, self.interaction)
        modal = self.interaction.response.send_modal.call_args.args[0]
        self.assertEqual(
            [option.value for option in modal.category_select.options], ["11", "31"]
        )
        self.assertEqual([option.value for option in modal.notify_roles.options], ["100"])

    async def test_no_available_category_reports_error_instead_of_opening_form(self):
        self.guild.categories = []
        await _open_party_modal(self.bot, self.interaction)
        self.interaction.response.send_modal.assert_not_awaited()
        self.interaction.response.send_message.assert_awaited_once()

    async def test_general_and_configured_private_categories_rejected_on_submit(self):
        self.settings.private_category = "私人測試"
        self.private.name = "私人測試"
        for category_id in ("21", "41"):
            with self.subTest(category_id=category_id):
                modal = self.modal()
                modal.category_select._values = [category_id]
                with patch.object(config, "DYNAMIC_VOICE_CREATE_ENABLED", True):
                    await modal.on_submit(self.interaction)
        self.guild.create_voice_channel.assert_not_awaited()
        self.assertEqual(self.interaction.response.send_message.await_count, 2)

    async def test_submission_rechecks_category_and_notification_role_permissions(self):
        for invalid_category, invalid_role in ((True, False), (False, True)):
            with self.subTest(category=invalid_category, role=invalid_role):
                modal = self.modal()
                if invalid_category:
                    modal.category_select._values = ["999"]
                if invalid_role:
                    modal.notify_roles._values = ["101"]
                with patch.object(config, "DYNAMIC_VOICE_CREATE_ENABLED", True):
                    await modal.on_submit(self.interaction)
        self.guild.create_voice_channel.assert_not_awaited()

    async def test_no_notification_roles_still_produces_a_valid_optional_dropdown(self):
        self.member.roles = []
        modal = self.modal()
        self.assertEqual(len(modal.children), 5)
        self.assertEqual(modal.notify_roles.options[0].value, "none")
        self.assertFalse(modal.notify_roles.required)

    async def test_multiple_selected_roles_are_saved_and_only_notified_on_share(self):
        another_role = Mock(spec=discord.Role)
        another_role.id = 102
        another_role.name = "湯技：墨繪術"
        another_role.mention = "<@&102>"
        another_category = Mock(spec=discord.CategoryChannel)
        another_category.id = 22
        another_category.name = another_role.name
        another_category.permissions_for.return_value = self.permissions
        self.guild.categories.append(another_category)
        self.guild.roles.append(another_role)
        self.member.roles.append(another_role)
        modal = self.modal([self.skill_role, another_role])
        components = modal.to_dict()["components"]
        values = {
            "room_category": ["31"],
            "room_name": "Room Name",
            "room_limit": "5",
            "room_note": "Note",
            "room_notify_roles": ["100", "102"],
        }
        for component in components:
            field = component["component"]
            key = "values" if field["type"] == 3 else "value"
            field[key] = values[field["custom_id"]]
        modal._refresh(self.interaction, components, {})
        with patch.object(config, "DYNAMIC_VOICE_CREATE_ENABLED", True):
            await modal.on_submit(self.interaction)
        party = self.bot.room_registry.register.call_args.kwargs["party"]
        self.assertEqual(party["notify_role_ids"], [100, 102])
        self.notification.send.assert_not_awaited()
        self.info["party"] = party
        view = self.interaction.followup.send.call_args.kwargs["view"]
        await view.share.callback(self.interaction)
        self.assertEqual(
            self.notification.send.call_args.kwargs["allowed_mentions"].roles,
            [self.skill_role, another_role],
        )
        self.assertEqual(
            self.notification.send.call_args.kwargs["content"], "<@&100> <@&102>"
        )

    async def test_created_room_permissions_allow_a_member_without_any_roles(self):
        self.member.roles = []
        with patch.object(config, "DYNAMIC_VOICE_CREATE_ENABLED", True):
            await self.modal().on_submit(self.interaction)
        overwrite = self.guild.create_voice_channel.call_args.kwargs["overwrites"][
            self.guild.default_role
        ]
        allow, deny = overwrite.pair()
        async with discord.Client(intents=discord.Intents.none()) as client:
            guild = discord.Guild(
                data={
                    "id": "10", "name": "Server", "owner_id": "1",
                    "roles": [{"id": "10", "name": "@everyone", "permissions": "0"}],
                },
                state=client._connection,
            )
            member = discord.Member(
                data={
                    "user": {
                        "id": "40", "username": "Member",
                        "discriminator": "0", "avatar": None,
                    },
                    "roles": [], "flags": 0,
                },
                guild=guild,
                state=client._connection,
            )
            room = discord.VoiceChannel(
                data={
                    "id": "77", "type": 2, "name": "Room", "parent_id": "11",
                    "position": 0, "bitrate": 64000, "user_limit": 5,
                    "permission_overwrites": [{
                        "id": "10", "type": 0,
                        "allow": str(allow.value), "deny": str(deny.value),
                    }],
                },
                guild=guild,
                state=client._connection,
            )
            permissions = room.permissions_for(member)
            self.assertTrue(permissions.view_channel)
            self.assertTrue(permissions.connect)
            self.assertTrue(permissions.speak)

    async def test_bot_mention_works_outside_game_category(self):
        message = SimpleNamespace(
            author=SimpleNamespace(bot=False),
            guild=self.guild,
            mentions=[self.bot.user],
            content="開房",
            channel=self.entry,
            reply=AsyncMock(),
        )
        self.entry.name = "general-chat"
        await PartyCommands(self.bot).on_message(message)
        message.reply.assert_awaited_once()
        self.assertIn("view", message.reply.call_args.kwargs)

    async def test_explicit_share_only_mentions_owned_skill_and_cannot_repeat(self):
        view = self.created_view([100])
        await view.share.callback(self.interaction)
        self.notification.send.assert_awaited_once()
        kwargs = self.notification.send.call_args.kwargs
        self.assertEqual(kwargs["content"], "<@&100>")
        self.assertEqual(kwargs["allowed_mentions"].roles, [self.skill_role])
        self.assertFalse(kwargs["allowed_mentions"].everyone)
        self.assertFalse(kwargs["allowed_mentions"].users)
        await view.share.callback(self.interaction)
        self.notification.send.assert_awaited_once()

    async def test_share_can_omit_role_mentions(self):
        view = self.created_view()
        await view.share.callback(self.interaction)
        kwargs = self.notification.send.call_args.kwargs
        self.assertIsNone(kwargs["content"])
        self.assertEqual(kwargs["allowed_mentions"].roles, [])

    async def test_share_can_use_specified_writable_text_channel(self):
        custom = Mock(spec=discord.TextChannel)
        custom.id = 33
        custom.guild = self.guild
        custom.permissions_for.return_value = self.permissions
        custom.send = AsyncMock()
        self.guild.get_channel.side_effect = lambda channel_id: (
            custom if channel_id == 33 else self.room
        )
        view = self.created_view()
        view.channel_select._values = [SimpleNamespace(id=33)]
        await view.share.callback(self.interaction)
        custom.send.assert_awaited_once()
        self.notification.send.assert_not_awaited()

    async def test_share_rejects_destination_without_bot_permission(self):
        self.notification.permissions_for.side_effect = lambda member: (
            self.permissions
            if member is self.member
            else SimpleNamespace(view_channel=True, send_messages=False, embed_links=True)
        )
        await self.created_view().share.callback(self.interaction)
        self.notification.send.assert_not_awaited()

    async def test_share_rejects_specified_destination_without_member_permission(self):
        self.notification.id = 20
        self.notification.permissions_for.return_value = SimpleNamespace(
            view_channel=False, send_messages=False
        )
        self.guild.get_channel.side_effect = lambda channel_id: (
            self.notification if channel_id == 20 else self.room
        )
        view = self.created_view()
        view.channel_select._values = [SimpleNamespace(id=20)]
        await view.share.callback(self.interaction)
        self.notification.send.assert_not_awaited()

    async def test_share_rejects_non_text_destination(self):
        view = self.created_view()
        view.channel_select._values = [SimpleNamespace(id=77)]
        await view.share.callback(self.interaction)
        self.notification.send.assert_not_awaited()

    async def test_share_rejects_destination_from_another_guild(self):
        self.notification.id = 20
        self.notification.guild = SimpleNamespace(id=11)
        self.guild.get_channel.side_effect = lambda channel_id: (
            self.notification if channel_id == 20 else self.room
        )
        view = self.created_view()
        view.channel_select._values = [SimpleNamespace(id=20)]
        await view.share.callback(self.interaction)
        self.notification.send.assert_not_awaited()

    async def test_share_rejects_non_skill_roles_and_roles_no_longer_owned(self):
        for role_id, roles in (
            ("101", [self.skill_role, self.level_role]),
            ("100", [self.level_role]),
        ):
            with self.subTest(role_id=role_id):
                self.member.roles = roles
                view = self.created_view([int(role_id)])
                await view.share.callback(self.interaction)
        self.notification.send.assert_not_awaited()

    async def test_share_rejects_other_owner_deleted_room_and_notice_permission(self):
        view = self.created_view()
        self.member.id = 41
        await view.share.callback(self.interaction)
        self.member.id = 40
        self.bot.room_registry.get.return_value = None
        await view.share.callback(self.interaction)
        self.bot.room_registry.get.return_value = self.info
        self.notification.permissions_for.return_value = SimpleNamespace(
            view_channel=True, send_messages=False
        )
        await view.share.callback(self.interaction)
        self.notification.send.assert_not_awaited()

    async def test_room_list_hides_rooms_without_access(self):
        self.bot.room_registry.entries.return_value = [(77, self.info)]
        self.room.permissions_for.return_value = SimpleNamespace(
            view_channel=False, connect=True
        )
        await _send_party_list(self.bot, self.interaction)
        self.assertNotIn(
            "embed", self.interaction.response.send_message.call_args.kwargs
        )

    async def test_room_list_displays_new_and_legacy_room_names(self):
        self.guild.get_member.return_value = self.member
        self.bot.room_registry.entries.return_value = [
            (77, {"owner": 40, "party": {"title": "New Room", "created_at": 1}}),
            (88, {"owner": 40, "party": {"game": "Game", "title": "Legacy", "created_at": 2}}),
        ]
        await _send_party_list(self.bot, self.interaction)
        embed = self.interaction.response.send_message.call_args.kwargs["embed"]
        self.assertIn("**New Room**", embed.description)
        self.assertIn("**Game｜Legacy**", embed.description)
        self.assertNotIn("遊戲｜New Room", embed.description)

    async def test_join_rechecks_permissions_before_moving_member(self):
        self.room.permissions_for.return_value = SimpleNamespace(
            view_channel=True, connect=False
        )
        self.member.move_to = AsyncMock()
        self.member.voice = SimpleNamespace(channel=Mock())
        view = PartyJoinConfirmView(self.bot, self.room)
        await view.join_party.callback(self.interaction)
        self.member.move_to.assert_not_awaited()

    async def test_panel_setup_creates_notification_only_once(self):
        self.general.text_channels = [self.entry]
        cog = PartyCommands(self.bot)
        with patch("cogs.slash.party.upsert_panel", new_callable=AsyncMock):
            await cog._refresh_panel(self.entry)
            self.general.text_channels.append(self.notification)
            await cog._refresh_panel(self.entry)
        self.general.create_text_channel.assert_awaited_once()

    async def test_panel_uses_saved_titles_instructions_and_button_labels(self):
        self.settings.party_panel_title = "Custom lobby"
        self.settings.party_panel_create_heading = "Start here"
        self.settings.party_panel_create_description = "Choose a category."
        self.settings.party_panel_create_label = "Create now"
        self.settings.party_panel_list_label = "Browse now"
        with patch("cogs.slash.party.upsert_panel", new_callable=AsyncMock) as upsert:
            await PartyCommands(self.bot)._refresh_panel(self.entry)
        embed = upsert.call_args.args[2]
        view = upsert.call_args.args[3]
        self.assertEqual(embed.title, "Custom lobby")
        self.assertEqual(embed.fields[0].name, "Start here")
        self.assertEqual(embed.fields[0].value, "Choose a category.")
        self.assertEqual([item.label for item in view.children], ["Create now", "Browse now"])

    async def test_missing_community_entry_reports_partial_setup(self):
        self.guild.text_channels = []
        with (
            patch("cogs.slash.party.upsert_panel", new_callable=AsyncMock),
            self.assertLogs("cogs.slash.party", level="WARNING"),
        ):
            ready = await PartyCommands(self.bot)._refresh_panel(self.entry)
        self.assertFalse(ready)
        self.general.create_text_channel.assert_not_awaited()


class SharedPanelTests(unittest.IsolatedAsyncioTestCase):
    async def test_title_changes_reuse_the_same_panel_by_component_identity(self):
        bot = Mock()
        existing = Mock(spec=discord.Message)
        existing.author = bot.user
        existing.embeds = [discord.Embed(title="Old custom title")]
        existing.components = [discord.ActionRow({
            "type": 1,
            "components": [{"type": 2, "style": 1, "label": "Create", "custom_id": "party:create"}],
        })]
        existing.pinned = True
        existing.edit = AsyncMock()
        unrelated = Mock(spec=discord.Message)
        unrelated.author = bot.user
        unrelated.embeds = [discord.Embed(title="New title")]
        unrelated.components = [discord.ActionRow({
            "type": 1,
            "components": [{"type": 2, "style": 2, "label": "Music", "custom_id": "skill_toggle:Music"}],
        })]
        channel = Mock(spec=discord.TextChannel)
        channel.pins.side_effect = lambda: _messages([unrelated, existing])
        channel.send = AsyncMock()
        for title in ("New title", "Another title"):
            await upsert_panel(
                bot, channel, discord.Embed(title=title), PartyPanelView(bot),
                component_prefix="party:",
            )
        self.assertEqual(existing.edit.await_count, 2)
        unrelated.edit.assert_not_called()
        channel.send.assert_not_awaited()

    async def test_rejects_dynamic_description_overflow_before_discord_request(self):
        channel = Mock(spec=discord.TextChannel)
        with self.assertRaisesRegex(ValueError, "exceeds Discord"):
            await upsert_panel(
                Mock(), channel, discord.Embed(description="x" * 4097), discord.ui.View(),
            )
        channel.pins.assert_not_called()

    async def test_reuses_old_pinned_panel_without_deleting_other_panels(self):
        bot = Mock()
        existing = Mock(spec=discord.Message)
        existing.author = bot.user
        existing.embeds = [discord.Embed(title="Room panel")]
        existing.pinned = True
        existing.edit = AsyncMock()
        unrelated = Mock(spec=discord.Message)
        unrelated.author = bot.user
        unrelated.embeds = [discord.Embed(title="Skill panel")]
        channel = Mock(spec=discord.TextChannel)
        channel.pins.return_value = _messages([unrelated, existing])
        channel.send = AsyncMock()
        await upsert_panel(
            bot, channel, discord.Embed(title="General room panel"), discord.ui.View(),
            previous_titles=("Room panel",),
        )
        existing.edit.assert_awaited_once()
        self.assertEqual(existing.edit.call_args.kwargs["embed"].title, "General room panel")
        unrelated.edit.assert_not_called()
        unrelated.delete.assert_not_called()
        existing.delete.assert_not_called()
        channel.send.assert_not_awaited()
        channel.history.assert_not_called()

    async def test_legacy_panel_is_updated_and_pinned(self):
        bot = Mock()
        message = Mock(spec=discord.Message)
        message.author = bot.user
        message.embeds = [discord.Embed(title="Room panel")]
        message.pinned = False
        message.edit = AsyncMock()
        message.pin = AsyncMock()
        channel = Mock(spec=discord.TextChannel)
        channel.pins.return_value = _messages([])
        channel.history.return_value = _messages([message])
        channel.send = AsyncMock()
        await upsert_panel(
            bot, channel, discord.Embed(title="Room panel"), discord.ui.View()
        )
        message.edit.assert_awaited_once()
        message.pin.assert_awaited_once()
        channel.send.assert_not_awaited()

    async def test_new_panel_supports_awaitable_pins_from_older_discord_versions(self):
        bot = Mock()
        message = Mock(spec=discord.Message)
        message.pinned = False
        message.pin = AsyncMock()
        channel = Mock(spec=discord.TextChannel)
        channel.pins = AsyncMock(return_value=[])
        channel.history.return_value = _messages([])
        channel.send = AsyncMock(return_value=message)
        await upsert_panel(
            bot, channel, discord.Embed(title="Room panel"), discord.ui.View()
        )
        channel.send.assert_awaited_once()
        message.pin.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()