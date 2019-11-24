from osuapi import OsuApi, AHConnector
from discord.ext import commands
from .utils import utils
import datetime
import discord
import logging
import aiohttp
import os

log = logging.getLogger(__name__)


class Core(commands.Cog):
    """
    The core of Nurevam, just essentials.
    """
    def __init__(self,bot):
        self.bot = bot
        self.redis=bot.db.redis
        self.bot.say_edit = bot.say

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

    def get_time_delta(self,person):
        delta = datetime.datetime.utcnow() - person
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        days, hours = divmod(hours, 24)
        if days:
            fmt = '{d} days, {h} hours, {m} minutes, and {s} seconds'
        else:
            fmt = '{h} hours, {m} minutes, and {s} seconds'

        return fmt.format(d=days, h=hours, m=minutes, s=seconds)


    @commands.command()
    async def uptime(self,ctx): #Showing Time that bot been total run
        """Prints the uptime."""
        await self.bot.say(ctx,content = "```py\nI have been up for {}\n```".format(self.get_bot_uptime()))

    @commands.command()
    async def prefix(self,ctx):
        prefix = (await self.redis.get("{}:Config:CMD_Prefix".format(ctx.message.guild.id)))
        prefix = set(prefix + ctx.prefix) #if user didnt set any, it will be default to ! which set prefix to be None? In case it is not, we can add current prefix to it.
        await self.bot.say(ctx,content = "```\n{}\n```".format(",".join(prefix)))

    @commands.command()
    async def info(self,ctx,*,person:discord.Member = None):
        """
        About Nurevam or person by mention info
        """

        if not person:
            guild = len(self.bot.guilds)
            member = len(set(self.bot.get_all_members()))
            app = await self.bot.application_info()
            msg = "Name:{}".format(self.bot.user)
            if ctx.message.guild.me.nick:
                msg += "\nNickname:{}".format(ctx.message.guild.me.nick)
            msg += "\nCreator: {}".format(app.owner)
            msg += "\nServer:{}\nMembers:{}".format(guild,member)
            link = "If you want to invite this bot to your server, you can check it out here <http://nurevam.site>!"
            return await self.bot.say(ctx,content = "```xl\n{}\n```\n{}\n".format(msg,link))
        else:
            e = discord.Embed()
            e.title = "{} - {}".format(person,person.id)
            e.set_thumbnail(url = person.avatar_url)
            e.add_field(name = "Created at", value="{} - ({})".format(person.created_at,self.get_time_delta(person.created_at)),inline=False)
            e.add_field(name = "Joined at", value="{} - ({})".format(person.joined_at,self.get_time_delta(person.joined_at)),inline=False)
            e.add_field(name = "Total Roles", value=str(len(person.roles)),inline=False)

            if person.colour.value:
                e.colour = person.color
            await self.bot.say(ctx,embed = e)

    @commands.command()
    async def serverinfo(self,ctx):
        """
        Give info about this server
        """
        g = ctx.guild
        embed = discord.Embed()
        embed.set_thumbnail(url = g.icon_url)
        embed.title = "{} - {}".format(g.name,g.id)
        embed.add_field(name = "Owner",value="{} - {}".format(g.owner,g.owner.id),inline=False)
        embed.add_field(name = "Created at", value = str(g.created_at), inline=False)
        embed.add_field(name = "Total Roles", value= str(len(g.roles)), inline=False)
        embed.add_field(name = "Total Members", value= str(g.member_count), inline=False)
        embed.add_field(name = "Premium Member", value= str(g.premium_subscription_count), inline=False)
        embed.add_field(name = "Premium Tier", value= str(g.premium_tier), inline=False)
        await self.bot.say(ctx,embed = embed)


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

    @commands.command(brief = "Showing which plugin is enable")
    async def plugin(self,ctx):
        """
        Red = Disable
        Blue = Enable

        Any problem such as plugins on dashboard is enable but show disable here, info Owner
        """
        special_case = {"Anime":"myanimelist","Anti Raid":"antiraid"}
        plugin_setting = await self.redis.hgetall("{}:Config:Cogs".format(ctx.message.guild.id))
        embed = discord.Embed()
        cogs = self.bot.cogs.keys()
        for x in cogs:
            setting =  	u"\U0001F534" #red
            if x in ("Core", "Remindme", "Tools", "REPL","Events"):  # A Owner's thing only.
                if ctx.message.author.id != self.bot.owner.id:
                    continue
                setting = u"\U0001F535" #blue
            if x.lower() in plugin_setting or special_case.get(x) in plugin_setting:
                setting =  	u"\U0001F535" #blue
            embed.add_field(name = x,value = setting)
        if ctx.message.guild.me.colour.value:
            embed.colour = ctx.message.guild.me.colour

        embed.set_footer(text = "{} = Disable | {} = Enable".format(u"\U0001F534",u"\U0001F535"))
        await ctx.send(embed=embed)

    @commands.command()
    @commands.cooldown(rate = 1,per=300,type =  commands.BucketType.user)
    async def feedback(self,ctx,*,msg):
        """
        Gives any feedback about bot. Cooldown: 5 min
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

    @commands.command(hidden=True)
    @commands.check(utils.is_owner)
    async def pm(self,ctx,user_id:int,*,msg):
        user = self.bot.get_user(user_id)
        print(user)
        print(msg)
        if user is None:
            return await ctx.send("User wasn't found.")
        message = "I have got a message from the owner,{}\n```fix\n{}\n```" \
                  "\n\nPlease note that the owner will not able to see any message of this before or after.\n" \
                  "To reply back, please use !reply <message>".format(self.bot.owner,msg)
        await user.send(message)
        await ctx.send(u"\U0001F44C")

    @commands.command(hidden = True)
    async def reply(self,ctx,*,msg):
        channel = self.bot.get_channel(295075318430040065)
        if channel is None:
            return await ctx.send("Appear so, reply system is down...")
        embed = discord.Embed()
        embed.set_author(name = ctx.message.author,icon_url=ctx.message.author.avatar_url)
        embed.add_field(name = "Author",value = "**ID**:{0.author.id}".format(ctx.message))
        embed.add_field(name = "Reply",value = msg,inline=False)
        await channel.send(embed=embed)
        await ctx.send(u"\U0001F44C")

def setup(bot):
    bot.add_cog(Core(bot))
