from discord.ext import commands
from .utils import utils
import discord
import asyncio
import datetime

class Core():
    """
    A core of Nurevam, just essentials.
    """
    def __init__(self,bot):
        self.bot = bot
        self.redis=bot.db.redis
        self.bot.say_edit = bot.says_edit


    def get_bot_uptime(self): #to calculates how long it been up
        now = datetime.datetime.utcnow()
        delta = now - self.bot.uptime
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        days, hours = divmod(hours, 24)
        if days:
            fmt = '{d} days, {h} hours, {m} minutes, and {s} seconds'
        else:
            fmt = '{h} hours, {m} minutes, and {s} seconds'

        return fmt.format(d=days, h=hours, m=minutes, s=seconds)

    @commands.command(hidden=True)
    async def uptime(self): #Showing Time that bot been total run
        """Tells you how long the bot has been up for."""
        await self.bot.say_edit("```py\nI have been up for {}\n```".format(self.get_bot_uptime()))

    @commands.command(name="prefix",hidden=True,pass_context=True)
    async def prefix(self,ctx):
        prefix = (await self.redis.get("{}:Config:CMD_Prefix".format(ctx.message.server.id)))
        await self.bot.says_edit("```\n{}\n```".format(prefix))

def setup(bot):
    bot.add_cog(Core(bot))