from discord.ext import commands
from .utils import utils
import discord
import asyncio
import datetime

class Test():
    """
    A TEST PURPOSE FOR TESTING COMMAND AND OTHER STUFF!
    """
    def __init__(self,bot):
        self.bot = bot
        self.redis=bot.db.redis
        self.bot.say_edit = bot.says_edit

    @commands.command(name="test",aliases=['okay',"what"])
    async def Testing(self,*,user:discord.Member):
        await self.bot.say("{} and {}".format(user.mention,user.name))


def setup(bot):
    bot.add_cog(Test(bot))