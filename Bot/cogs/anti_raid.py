from discord.ext import commands
from .utils import utils
import datetime
import asyncio
import discord
import logging

log = logging.getLogger(__name__)

class Mod():
    """
    A mod tool for Mods.
    """
    def __init__(self, bot):
        self.bot = bot
        self.redis = bot.db.redis
        self.bot.say_edit = bot.say
        self.config = {}
        self.bg = utils.Background("anti raid",60,30,self.bg_event,log)
        self.bot.background.update({"anti raid":self.bg})
        self.bg.start()


    def __unload(self):
        self.bg.stop()

    async def bg_event(self):
        guild_list = await self.redis.smembers("Info:AntiRaid")
        for x in guild_list:
            if await self.redis.hget("{}:Config:Cogs".format(x),"Anti-Raid") == "on":
                config = await self.redis.hgetall("{}:AntiRaid:Config".format(x))
                self.config.update({int(x):config})

    async def security_level(self,member,mode,reason):
        #get level of mode
        #there will be 5 level
        #0 is nothing
        #1 is warning user
        #2 is role grant
        #3 is kick
        #4 is softban
        #5 is ban
        level = 0
        try:
            if level == 4 or level == 5:
                member.ban(reason = reason)
                if level == 4:
                    member.unban(reason = reason)
            elif level == 3:
                member.kick(reason = reason)
            elif level == 2:
                #get role here
                role = None
                member.add_roles(role,reason = reason)
            elif level == 1:
                #warn user
                pass
            else:
                pass
        except: #no perm? oh well
            pass

    async def on_message(self,msg):
        if msg.author.id == self.bot.user.id and isinstance(msg.channel,discord.DMChannel):
            return

        #checking invite link and delete it if it not allow.
        if "discord.gg/" in msg.content:
            if self.config.get(msg.guild.id) and self.config[msg.guild.id].get("invite"):
                list_invite = await msg.guild.invites()
                if len([x for x in list_invite if x.code in msg.content]) is 0:
                    await msg.channel.send("Invite link are not allowed!")

        #checking if person spamming
        # if self.config.get(msg.guild.id) and self.config[msg.guild.id].get("invite"):
        count = await self.redis.hincrby("{0.guild.id}:Mod:Raid:{0.author.id}".format(msg),msg.content)

        if await self.redis.ttl("{0.guild.id}:Mod:Raid:{0.author.id}".format(msg)) == -1:
            print("setting expire")
        print(count)
        if int(count) >= 5:
            await msg.channel.send("STOP IT!")

    async def on_member_join(self,member):
            created = member.created_at
            current = datetime.datetime.utcnow()
            age = current - created
            print(age)
            if int(age.total_seconds()) <= 600:
                await member.ban(reason = "Account is under requirement 10 min old")

# def setup(bot):
#     bot.add_cog(Mod(bot))