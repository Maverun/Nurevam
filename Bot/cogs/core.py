from osuapi import OsuApi, AHConnector
from discord.ext import commands
from .utils import utils
import datetime
import discord
import logging
import aiohttp
import os

log = logging.getLogger(__name__)


class Core():
    """
    The core of Nurevam, just essentials.
    """
    def __init__(self,bot):
        self.bot = bot
        self.redis=bot.db.redis
        self.bot.say_edit = bot.say
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
    async def uptime(self,ctx): #Showing Time that bot been total run
        """Prints the uptime."""
        await self.bot.say(ctx,content = "```py\nI have been up for {}\n```".format(self.get_bot_uptime()))

    @commands.command(hidden=True)
    async def prefix(self,ctx):
        prefix = (await self.redis.get("{}:Config:CMD_Prefix".format(ctx.message.guild.id)))
        await self.bot.say(ctx,ccontent = "```\n{}\n```".format(prefix))

    @commands.command(hidden=True)
    async def info(self,ctx):
        guild = len(self.bot.guilds)
        member = len(set(self.bot.get_all_members()))
        app = await self.bot.application_info()
        msg = "Name:{}".format(self.bot.user)
        if ctx.message.guild.me.nick:
            msg += "\nNickname:{}".format(ctx.message.guild.me.nick)
        msg += "\nCreator: {}".format(app.owner)
        msg += "\nServer:{}\nMembers:{}".format(guild,member)
        link = "If you want to invite this bot to your sever, you can check it out here <http://nurevam.site>!"
        await self.bot.say(ctx,content = "```xl\n{}\n```\n{}".format(msg,link))

    async def check_status(self,link):
        with aiohttp.ClientSession() as session:
            async with session.get(link) as resp:
                log.debug(resp.status)
                if resp.status == 200:
                    return True
                else:
                    return False

    @commands.group(hidden=True,invoke_without_command=True)
    async def profile(self,ctx):
        setting = await self.redis.hgetall("Profile:{}".format(ctx.message.author.id))
        info = []
        if setting:
            for x in setting:
                info.append("{}: {}".format(x,setting[x]))
            msg = "To register, you can do !profile add osu <username here>"
            await ctx.author.send("```xl\n{}\n```\n{}".format("\n".join(info),msg))
        else:
            await self.bot.say(ctx,content = "You didn't add any data! Make sure you add something first!")

    @profile.command()
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
                await ctx.send("Done.")
            else:
                await ctx.send("This isn't a valid username, please double check")
        else:
            await ctx.send("Please double check! The only databases so far are \n{}".format(",".join(default)))

    @commands.command(hidden=True)
    async def command(self,ctx):
        """
        Type !help {command} for more info on a command.
        You can also type !help {category} for more info on a category.
        For example, !help level (If you have level plugin enable!)
        """
        await ctx.send("Yes this is a command.")

    @commands.command(hidden=True)
    async def category(self,ctx):
        """
        Type !help command for additional info on a command.
        You can also type !help category for additional info on a category.
        For example, type !help Level (If you have the level plugin enable!)

        """
        await ctx.send("Yes this is a category.")

    @commands.command(hidden = True)
    async def plugin(self,ctx):
        plugin_setting = await self.redis.hgetall("{}:Config:Cogs".format(ctx.message.guild.id))
        embed = discord.Embed()
        cogs = [x.lower() for x in list(self.bot.cogs.keys())]
        files_cogs = [x.strip(".py") for x in os.listdir("cogs") if ".py" in x and x != "__init__.py"]
        print(files_cogs)
        for x in files_cogs:
            setting =  	u"\U0001F534"
            if x in cogs:
                if x in ("core", "remindme", "tools", "repl","events"):  # A Owner's thing only.
                    if ctx.message.author.id != self.bot.owner.id:
                        continue
                    setting = u"\U0001F535"
                if x in plugin_setting:
                    setting =  	u"\U0001F535"
            else:
                setting = u"\u26AA"
            embed.add_field(name = x,value = setting)
        if ctx.message.guild.me.colour.value:
            embed.colour = ctx.message.guild.me.colour

        await ctx.send(embed=embed)

    @commands.command()
    @commands.cooldown(rate = 1,per=300,type =  commands.BucketType.user)
    async def feedback(self,ctx,*,msg):
        """
        Gives any feedback about bot.
        For example, reporting bot, new idea/suggestions.
        A quicker way to get hold of owner without joining server.

        Sooner or later, bot may(not) contact you via PMS about status of your requests.

        Only able to make feedback once a five minute.
        """
        embed = discord.Embed()
        embed.set_author(name = ctx.message.author,icon_url=ctx.message.author.avatar_url or ctx.message.author.default_avatar_url)
        embed.add_field(name = "Author",value = "**ID**:{0.id}".format(ctx.message))
        embed.add_field(name = "Server",value = "**Name**:{0.guild.name}\n**ID**:{0.guild.id}\n**Channel**:{0.channel.name} - {0.channel.id}".format(ctx.message))
        embed.add_field(name = "Feedback",value = msg)

        channel = self.bot.get_channel(292133726370922497)
        await channel.send(embed=embed)
        await ctx.send(u"\U0001F44C"+", Thank you for your valuable feedback. \nHopefully, the owner will reply to you soon.")

    @commands.command()
    @commands.check(utils.is_owner)
    async def pm(self,ctx,user_id:int,*,msg):
        user = self.bot.get_user(user_id)
        print(user)
        print(msg)
        if user is None:
            return await ctx.send("User wasn't found.")
        message = "I have got a message from the owner,{}\n```fix\n{}\n```" \
                  "\n\nPlease note that the owner will not able to see any message of this before or after.\n" \
                  "To reply back, please use {}reply <message>".format(self.bot.owner,msg,ctx.prefix)
        await user.send(message)

    @commands.command(hidden = True)
    async def reply(self,ctx,*,msg):
        channel = self.bot.get_channel(295075318430040065)
        if channel is None:
            return await ctx.send("Appear so, reply system is down...")
        embed = discord.Embed()
        embed.set_author(name = ctx.message.author,icon_url=ctx.message.author.avatar_url or ctx.message.author.default_avatar_url)
        embed.add_field(name = "Author",value = "**ID**:{0.id}".format(ctx.message))
        embed.add_field(name = "Reply",value = msg,inline=False)
        await channel.send(embed=embed)
        await ctx.send(u"\U0001F44C")

def setup(bot):
    bot.add_cog(Core(bot))
