import discord
from discord.ext import commands


class General(commands.Cog):
    """基本指令模組"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="ping")
    async def ping(self, ctx: commands.Context):
        """查看機器人延遲"""
        latency = round(self.bot.latency * 1000)
        await ctx.send(f"🏓 Pong! 延遲: {latency}ms")

    @commands.command(name="info")
    async def info(self, ctx: commands.Context):
        """查看機器人資訊"""
        embed = discord.Embed(
            title="🤖 機器人資訊",
            color=discord.Color.blue(),
        )
        embed.add_field(name="伺服器數量", value=str(len(self.bot.guilds)))
        embed.add_field(name="延遲", value=f"{round(self.bot.latency * 1000)}ms")
        embed.set_footer(text=f"Requested by {ctx.author}")
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(General(bot))
