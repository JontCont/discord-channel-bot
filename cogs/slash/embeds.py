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
