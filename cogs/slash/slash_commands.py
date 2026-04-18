import discord
from discord import app_commands
from discord.ext import commands


class SlashCommands(commands.Cog):
    """Slash 指令模組"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="userinfo", description="查看使用者資訊")
    @app_commands.describe(member="要查看的使用者")
    async def userinfo(
        self,
        interaction: discord.Interaction,
        member: discord.Member | None = None,
    ):
        target = member or interaction.user
        embed = discord.Embed(
            title=f"👤 {target.display_name}",
            color=target.color,
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="ID", value=str(target.id))
        embed.add_field(name="加入時間", value=target.joined_at.strftime("%Y-%m-%d"))
        embed.add_field(name="帳號建立", value=target.created_at.strftime("%Y-%m-%d"))
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(SlashCommands(bot))
