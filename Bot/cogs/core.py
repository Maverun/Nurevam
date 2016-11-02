from osuapi import OsuApi, AHConnector
from discord.ext import commands
from .utils import utils
import datetime
import discord
import asyncio
import aiohttp

class Core():
    """
    A core of Nurevam, just essentials.
    """
    def __init__(self,bot):
        self.bot = bot
        self.redis=bot.db.redis
        self.bot.say_edit = bot.says_edit
        self.api = OsuApi(utils.secret["osu"], connector=AHConnector())

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

    @commands.command(hidden=True,pass_context=True)
    async def prefix(self,ctx):
        prefix = (await self.redis.get("{}:Config:CMD_Prefix".format(ctx.message.server.id)))
        await self.bot.says_edit("```\n{}\n```".format(prefix))

    @commands.command(hidden=True,pass_context=True)
    async def info(self,ctx):
        server = len(self.bot.servers)
        member = len(set(self.bot.get_all_members()))
        app = await self.bot.application_info()
        msg = "Name:{}".format(self.bot.user)
        if ctx.message.server.me.nick:
            msg += "\nNickname:{}".format(ctx.message.server.me.nick)
        msg += "\nCreator: {}".format(app.owner)
        msg += "\nServer:{}\nMembers:{}".format(server,member)
        link = "If you want to invite this bot to your sever, you can check it out here <http://nurevam.site>!"
        await self.bot.say("```xl\n{}\n```\n{}".format(msg,link))


    async def check_status(self,link):
        with aiohttp.ClientSession() as session:
            async with session.get(link) as resp:
                if resp.status == 200:
                    return True
                else:
                    return False

    @commands.group(hidden=True,pass_context=True,invoke_without_command=True)
    async def profile(self,ctx):
        setting = await self.redis.hgetall("Profile:{}".format(ctx.message.author.id))
        info = []
        if setting:
            for x in setting:
                info.append("{}: {}".format(x,setting[x]))
            msg = "To register, you can do !profile add osu <username here>"
            await self.bot.whisper("```xl\n{}\n```\n{}".format("\n".join(info),msg))
        else:
            await self.bot.say("You didn't add any! Make sure you add something first!")

    @profile.command(pass_context=True)
    async def add(self,ctx,plugin,name):
        # setting = await self.redis.hgetall("Profile:{}".format(ctx.message.author.id))
        print("OKAY HERE")
        default = ["myanimelist","osu"]
        check = False
        if plugin in default:
            print("check")
            print(name)
            if plugin == "myanimelist":
                check = await self.check_status("http://myanimelist.net/profile/{}".format(name))
            elif plugin == "osu":
                results = await self.api.get_user(name)
                print(results)
                if results == []:
                    print("failed")
                    pass
                else:
                    check = True
            if check:
                await self.redis.hset("Profile:{}".format(ctx.message.author.id),plugin,name)
                await self.bot.says_edit("Done.")
            else:
                await self.bot.says_edit("There is no such a username like that, please double check")
        else:
            await self.bot.says_edit("Please double check! There is so far only \n{}".format(",".join(default)))

    @commands.command(hidden=True)
    async def command(self):
        """
        Type !help {command} for more info on a command.
        You can also type !help {category} for more info on a category.
        For example, !help level (If you have level plugin enable!)
        """
        await self.bot.say("Yes this is a command.")

    @commands.command(hidden=True)
    async def category(self):
        """
        Type !help command for more info on a command.
        You can also type !help category for more info on a category.
        For example, !help Level (If you have level plugin enable!)

        """
        await self.bot.say("Yes this is a category.")

def setup(bot):
    bot.add_cog(Core(bot))
