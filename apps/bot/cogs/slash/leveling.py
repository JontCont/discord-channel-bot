import logging
import random
import time
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands, tasks

logger = logging.getLogger("bot.leveling")

from config import LEVELING_DB_PATH
from cogs.repository.leveling_db import LevelingDB
from cogs.service.guild_settings_service import GuildSettings


def _progress_bar(current: int, total: int, length: int = 16) -> str:
    if total <= 0:
        return "▓" * length
    filled = int(length * current / total)
    filled = max(0, min(filled, length))
    return "▓" * filled + "░" * (length - filled)


def _streak_multiplier(streak: int) -> float:
    if streak >= 30:
        return 2.0
    if streak >= 7:
        return 1.5
    return 1.0


class Leveling(commands.Cog):
    """活躍值等級系統"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = LevelingDB(LEVELING_DB_PATH)
        # (guild_id, user_id) -> last message XP timestamp (in-memory fast check)
        self._msg_cooldowns: dict[tuple[int, int], float] = {}
        self._voice_next_due: dict[int, float] = {}

    async def cog_load(self):
        await self.db.init()
        self.voice_xp_loop.start()
        logger.info("Leveling cog loaded — on_message listener active")

    async def cog_unload(self):
        self.voice_xp_loop.cancel()
        await self.db.close()

    # ── Milestone role helpers ───────────────────────────────

    def _get_milestone(
        self, level: int, level_roles: tuple[tuple[int, str, int], ...]
    ) -> tuple[int, str, int] | None:
        """Return the highest milestone <= level."""
        result = None
        for lv, name, color in level_roles:
            if lv <= level:
                result = (lv, name, color)
        return result

    def _all_milestone_names(
        self, level_roles: tuple[tuple[int, str, int], ...]
    ) -> set[str]:
        return {name for _, name, _ in level_roles}

    async def _update_roles(
        self,
        member: discord.Member,
        new_level: int,
        level_roles: tuple[tuple[int, str, int], ...],
    ):
        """Assign the correct milestone role and remove outdated ones."""
        milestone = self._get_milestone(new_level, level_roles)
        if not milestone:
            return

        _, target_name, target_color = milestone
        all_names = self._all_milestone_names(level_roles)

        to_remove = [r for r in member.roles if r.name in all_names and r.name != target_name]
        target_role = discord.utils.get(member.guild.roles, name=target_name)

        # Create role if it doesn't exist
        if not target_role:
            target_role = await member.guild.create_role(
                name=target_name,
                color=discord.Color(target_color),
                reason="Leveling: auto-create milestone role",
            )

        if to_remove:
            await member.remove_roles(*to_remove, reason="Leveling: milestone update")
        if target_role not in member.roles:
            await member.add_roles(target_role, reason="Leveling: milestone update")

    # ── Level-up announcement ────────────────────────────────

    async def _announce_levelup(
        self,
        member: discord.Member,
        old_level: int,
        new_level: int,
        settings: GuildSettings,
    ):
        milestone = self._get_milestone(new_level, settings.level_roles)
        title_name = milestone[1] if milestone else f"LV{new_level}"

        _, xp_needed = self.db.xp_to_next(
            self.db.xp_for_level(new_level), new_level
        )

        embed = discord.Embed(
            title="🎉 升級啦！",
            description=(
                f"{member.mention} 升到了 **LV{new_level}**！\n"
                f"稱號：**{title_name}**\n\n"
                f"{_progress_bar(0, xp_needed)} `0/{xp_needed} XP`"
            ),
            color=discord.Color(milestone[2]) if milestone else discord.Color.gold(),
        )
        embed.set_thumbnail(url=member.display_avatar.url)

        # Check if this is a milestone level
        is_milestone = any(lv == new_level for lv, _, _ in settings.level_roles)
        if is_milestone:
            embed.set_footer(text="🏅 里程碑達成！恭喜獲得新稱號！")

        channel = discord.utils.get(
            member.guild.text_channels, name=settings.levelup_channel
        )
        if channel:
            await channel.send(embed=embed)

    # ── XP from messages ─────────────────────────────────────

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        settings = await self.bot.guild_settings_service.get(message.guild.id)
        now = time.time()
        cooldown_key = (message.guild.id, message.author.id)
        last = self._msg_cooldowns.get(cooldown_key, 0)
        if now - last < settings.xp_message_cooldown:
            logger.debug(
                "XP cooldown: user=%s remaining=%.0fs",
                message.author,
                settings.xp_message_cooldown - (now - last),
            )
            return

        self._msg_cooldowns[cooldown_key] = now
        xp = random.randint(settings.xp_per_message_min, settings.xp_per_message_max)

        try:
            result = await self.db.add_xp(message.author.id, message.guild.id, xp)
        except Exception:
            logger.exception("Failed to add XP for user %s", message.author)
            return

        logger.info(
            "XP awarded: user=%s xp=+%d total=%d level=%d",
            message.author, xp, result["xp"], result["level"],
        )

        if result["level"] > result["old_level"]:
            await self._update_roles(
                message.author, result["level"], settings.level_roles
            )
            await self._announce_levelup(
                message.author, result["old_level"], result["level"], settings
            )

    # ── XP from voice ────────────────────────────────────────

    @tasks.loop(seconds=30)
    async def voice_xp_loop(self):
        """Award XP to members in voice channels (≥2 non-bot members)."""
        now = time.monotonic()
        active_guild_ids = {guild.id for guild in self.bot.guilds}
        for guild_id in self._voice_next_due.keys() - active_guild_ids:
            del self._voice_next_due[guild_id]

        for guild in self.bot.guilds:
            settings = await self.bot.guild_settings_service.get(guild.id)
            if now < self._voice_next_due.get(guild.id, now):
                continue

            self._voice_next_due[guild.id] = now + settings.xp_voice_interval
            for vc in guild.voice_channels:
                real_members = [m for m in vc.members if not m.bot]
                if len(real_members) < 2:
                    continue
                for member in real_members:
                    result = await self.db.add_xp(
                        member.id, guild.id, settings.xp_per_voice_tick
                    )
                    if result["level"] > result["old_level"]:
                        await self._update_roles(
                            member, result["level"], settings.level_roles
                        )
                        await self._announce_levelup(
                            member,
                            result["old_level"],
                            result["level"],
                            settings,
                        )

    @voice_xp_loop.before_loop
    async def before_voice_xp(self):
        await self.bot.wait_until_ready()

    # ── /daily ───────────────────────────────────────────────

    @app_commands.command(
        name="daily",
        description="每日簽到領取活躍值 XP（累積連續天數享倍率加成）",
    )
    async def daily(self, interaction: discord.Interaction):
        settings = await self.bot.guild_settings_service.get(interaction.guild.id)
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        result = await self.db.do_daily(interaction.user.id, interaction.guild.id, today)

        if result is None:
            await interaction.response.send_message(
                "⏳ 你今天已經簽到過了，明天再來吧！", ephemeral=True
            )
            return

        streak = result["streak"]
        multiplier = _streak_multiplier(streak)
        xp = int(settings.xp_daily_base * multiplier)

        xp_result = await self.db.add_xp(
            interaction.user.id, interaction.guild.id, xp
        )

        streak_text = f"🔥 連續簽到 **{streak}** 天" if streak > 1 else "第 1 天簽到"
        bonus_text = f"（×{multiplier} 加成！）" if multiplier > 1 else ""

        embed = discord.Embed(
            title="📅 每日簽到成功！",
            description=(
                f"{streak_text}{bonus_text}\n"
                f"獲得 **+{xp} XP**\n\n"
                f"目前等級：**LV{xp_result['level']}**"
            ),
            color=discord.Color.green(),
        )

        if streak >= 7:
            embed.set_footer(text="💡 連續 7 天 ×1.5 | 連續 30 天 ×2.0")

        await interaction.response.send_message(embed=embed)

        if xp_result["level"] > xp_result["old_level"]:
            await self._update_roles(
                interaction.user, xp_result["level"], settings.level_roles
            )
            await self._announce_levelup(
                interaction.user,
                xp_result["old_level"],
                xp_result["level"],
                settings,
            )

    # ── /rank ────────────────────────────────────────────────

    @app_commands.command(
        name="rank",
        description="查看個人或指定成員的等級、稱號、排名與升級進度",
    )
    @app_commands.describe(member="要查看的成員（留空則查詢自己）")
    async def rank(
        self,
        interaction: discord.Interaction,
        member: discord.Member | None = None,
    ):
        target = member or interaction.user
        settings = await self.bot.guild_settings_service.get(interaction.guild.id)
        user = await self.db.get_user(target.id, interaction.guild.id)
        rank_pos = await self.db.get_rank(target.id, interaction.guild.id)

        xp_into, xp_needed = self.db.xp_to_next(user["xp"], user["level"])
        milestone = self._get_milestone(user["level"], settings.level_roles)
        title_name = milestone[1] if milestone else f"LV{user['level']}"

        bar = _progress_bar(xp_into, xp_needed)
        if user["level"] >= 50:
            progress_text = "✨ MAX LEVEL ✨"
        else:
            progress_text = f"{bar} `{xp_into}/{xp_needed} XP`"

        embed = discord.Embed(
            title=f"📊 {target.display_name} 的等級資訊",
            color=discord.Color(milestone[2]) if milestone else discord.Color.blue(),
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="等級", value=f"**LV{user['level']}**", inline=True)
        embed.add_field(name="排名", value=f"#{rank_pos}", inline=True)
        embed.add_field(name="總 XP", value=f"{user['xp']:,}", inline=True)
        embed.add_field(name="稱號", value=title_name, inline=True)
        embed.add_field(
            name="連續簽到",
            value=f"🔥 {user['daily_streak']} 天" if user["daily_streak"] > 0 else "—",
            inline=True,
        )
        embed.add_field(name="升級進度", value=progress_text, inline=False)

        await interaction.response.send_message(embed=embed)

    # ── /leaderboard ─────────────────────────────────────────

    @app_commands.command(
        name="leaderboard",
        description="查看伺服器活躍值排行榜 TOP 10",
    )
    async def leaderboard(self, interaction: discord.Interaction):
        top = await self.db.get_leaderboard(interaction.guild.id, limit=10)
        if not top:
            await interaction.response.send_message(
                "📊 目前還沒有任何活躍資料。", ephemeral=True
            )
            return

        lines = []
        medals = {1: "🥇", 2: "🥈", 3: "🥉"}
        for i, entry in enumerate(top, 1):
            user = self.bot.get_user(entry["user_id"])
            name = user.display_name if user else f"<@{entry['user_id']}>"
            prefix = medals.get(i, f"`#{i:>2}`")
            lines.append(
                f"{prefix} **{name}** — LV{entry['level']}（{entry['xp']:,} XP）"
            )

        embed = discord.Embed(
            title="🏆 活躍值排行榜 TOP 10",
            description="\n".join(lines),
            color=discord.Color.gold(),
        )
        await interaction.response.send_message(embed=embed)

    # ── /level-preview ───────────────────────────────────────

    @app_commands.command(
        name="level-preview",
        description="預覽升級公告、等級卡與排行榜的顯示效果（需管理角色權限）",
    )
    @app_commands.checks.has_permissions(manage_roles=True)
    async def level_preview(self, interaction: discord.Interaction):
        member = interaction.user
        settings = await self.bot.guild_settings_service.get(interaction.guild.id)

        # 1. Level-up embed (milestone)
        preview_role_index = min(2, len(settings.level_roles) - 1)
        milestone_lv, milestone_name, milestone_color = settings.level_roles[
            preview_role_index
        ]
        milestone_xp = self.db.xp_for_level(milestone_lv)
        _, xp_needed = self.db.xp_to_next(milestone_xp, milestone_lv)
        preview_progress = min(420, xp_needed)
        levelup_embed = discord.Embed(
            title="🎉 升級啦！",
            description=(
                f"{member.mention} 升到了 **LV{milestone_lv}**！\n"
                f"稱號：**{milestone_name}**\n\n"
                f"{_progress_bar(0, xp_needed)} `0/{xp_needed} XP`"
            ),
            color=discord.Color(milestone_color),
        )
        levelup_embed.set_thumbnail(url=member.display_avatar.url)
        levelup_embed.set_footer(text="🏅 里程碑達成！恭喜獲得新稱號！")

        # 2. Rank card embed
        rank_embed = discord.Embed(
            title=f"📊 {member.display_name} 的等級資訊",
            color=discord.Color(milestone_color),
        )
        rank_embed.set_thumbnail(url=member.display_avatar.url)
        rank_embed.add_field(
            name="等級", value=f"**LV{milestone_lv}**", inline=True
        )
        rank_embed.add_field(name="排名", value="#3", inline=True)
        rank_embed.add_field(
            name="總 XP",
            value=f"{milestone_xp + preview_progress:,}",
            inline=True,
        )
        rank_embed.add_field(name="稱號", value=milestone_name, inline=True)
        rank_embed.add_field(name="連續簽到", value="🔥 7 天", inline=True)
        rank_embed.add_field(
            name="升級進度",
            value=(
                f"{_progress_bar(preview_progress, xp_needed)} "
                f"`{preview_progress}/{xp_needed} XP`"
            ),
            inline=False,
        )

        # 3. Leaderboard embed
        lb_embed = discord.Embed(
            title="🏆 活躍值排行榜 TOP 10",
            description=(
                f"🥇 **{member.display_name}** — LV25（22,538 XP）\n"
                f"🥈 **範例用戶 B** — LV20（13,925 XP）\n"
                f"🥉 **範例用戶 C** — LV15（7,505 XP）\n"
                f"`# 4` **範例用戶 D** — LV10（3,158 XP）\n"
                f"`# 5` **範例用戶 E** — LV5（726 XP）"
            ),
            color=discord.Color.gold(),
        )

        await interaction.response.send_message(
            content="**以下是等級系統各功能的預覽：**\n\n"
                f"**① 升級公告**（發送至 #{settings.levelup_channel}）",
            embed=levelup_embed,
            ephemeral=True,
        )
        await interaction.followup.send(
            content="**② 等級卡** `/rank`",
            embed=rank_embed,
            ephemeral=True,
        )
        await interaction.followup.send(
            content="**③ 排行榜** `/leaderboard`",
            embed=lb_embed,
            ephemeral=True,
        )

    @level_preview.error
    async def level_preview_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "🚫 你需要「管理角色」權限才能使用此指令。", ephemeral=True
            )

    # ── /level-init ──────────────────────────────────────────

    @app_commands.command(
        name="level-init",
        description="為伺服器所有現有成員初始化等級資料並分配 LV1 身分組（需管理角色權限）",
    )
    @app_commands.checks.has_permissions(manage_roles=True)
    async def level_init(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        settings = await self.bot.guild_settings_service.get(guild.id)

        initialized = 0
        skipped = 0

        for member in guild.members:
            if member.bot:
                continue

            user = await self.db.get_user(member.id, guild.id)

            # Check if member already has any level role
            has_level_role = any(
                r.name in self._all_milestone_names(settings.level_roles)
                for r in member.roles
            )

            if has_level_role and user["xp"] > 0:
                skipped += 1
                continue

            await self._update_roles(member, user["level"], settings.level_roles)
            initialized += 1

        await interaction.followup.send(
            f"✅ 初始化完成！\n"
            f"　• 已分配身分組：**{initialized}** 位成員\n"
            f"　• 已跳過（已有等級）：**{skipped}** 位成員",
            ephemeral=True,
        )

    @level_init.error
    async def level_init_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ):
        if isinstance(error, app_commands.MissingPermissions):
            if interaction.response.is_done():
                await interaction.followup.send(
                    "🚫 你需要「管理角色」權限才能使用此指令。", ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    "🚫 你需要「管理角色」權限才能使用此指令。", ephemeral=True
                )


async def setup(bot: commands.Bot):
    await bot.add_cog(Leveling(bot))
