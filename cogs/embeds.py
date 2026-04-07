import discord
from discord import app_commands
from discord.ext import commands


class Embeds(commands.Cog):
    """Embed 訊息模組"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="announce", description="發送公告 Embed 訊息")
    @app_commands.describe(title="公告標題", content="公告內容")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def announce(
        self,
        interaction: discord.Interaction,
        title: str,
        content: str,
    ):
        embed = discord.Embed(
            title=f"📢 {title}",
            description=content,
            color=discord.Color.gold(),
        )
        embed.set_footer(text=f"由 {interaction.user.display_name} 發布")
        await interaction.channel.send(embed=embed)
        await interaction.response.send_message("✅ 公告已發送！", ephemeral=True)

    @app_commands.command(name="poll", description="建立簡易投票")
    @app_commands.describe(question="投票問題", option_a="選項 A", option_b="選項 B")
    async def poll(
        self,
        interaction: discord.Interaction,
        question: str,
        option_a: str,
        option_b: str,
    ):
        embed = discord.Embed(
            title=f"📊 {question}",
            color=discord.Color.purple(),
        )
        embed.add_field(name="🅰️ 選項 A", value=option_a, inline=False)
        embed.add_field(name="🅱️ 選項 B", value=option_b, inline=False)
        embed.set_footer(text=f"由 {interaction.user.display_name} 發起")

        await interaction.response.send_message(embed=embed)
        msg = await interaction.original_response()
        await msg.add_reaction("🅰️")
        await msg.add_reaction("🅱️")

    @announce.error
    async def announce_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "🚫 你需要「管理訊息」權限才能使用此指令。", ephemeral=True
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(Embeds(bot))
