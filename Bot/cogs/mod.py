from discord.ext import commands
from .utils import utils
import asyncio
import discord

def check_roles(msg):
    if msg.message.author.id == "105853969175212032":
        return True
    Admin = utils.check_roles(msg, "Mod", "admin_roles")
    return Admin or msg.message.author.id == "105853969175212032"

def is_enable(msg): #Checking if cogs' config for this server is off or not
    return utils.is_enable(msg, "mod")or msg.message.author.id == "105853969175212032"

class Mod():
    """
    A Mod tools for Mod.
    """
    def __init__(self, bot):
        self.bot = bot
        self.bot.say_edit = bot.says_edit

    def delete_mine(self,m):
        return m.author == self.bot.user


#########################################
#     _____   _                         #
#    / ____| | |                        #
#   | |      | |   ___    __ _   _ __   #
#   | |      | |  / _ \  / _` | | '_ \  #
#   | |____  | | |  __/ | (_| | | | | | #
#    \_____| |_|  \___|  \__,_| |_| |_| #
#########################################

    @commands.group(brief="Allow to clean bot itself",pass_context=True,invoke_without_command=True)
    @commands.check(is_enable)
    @commands.check(check_roles)
    async def clean(self, ctx, *, limit:int=100):
        """
        Allow to clear up it's own message.
        Does not affect any user's message.
        """
        counter = 0
        if ctx.message.channel.is_private or ctx.message.channel.permissions_for(ctx.message.server.me).manage_messages is False:
            async for message in self.bot.logs_from(ctx.message.channel,limit=limit):
                if self.bot.user.id == message.author.id:
                    try:
                        await self.bot.delete_message(message)
                        await asyncio.sleep(0.25)
                        counter +=1
                    except:
                        await asyncio.sleep(0.40)
                        await self.bot.delete_message(message)
                        continue
        else:
            counter = await self.bot.purge_from(ctx.message.channel,check=self.delete_mine)
            counter= len(counter)
        await self.bot.say("```py\nClean up message: {}\n```".format(counter))

    @clean.command(pass_context=True, invoke_without_command=True)
    @commands.check(is_enable)
    @commands.check(check_roles)
    @commands.bot_has_permissions(manage_messages=True)
    async def role(self,ctx,role : discord.Role,*,limit: int=100):
        """
        <prefix> role <what role it is> <optional, but how many, default 100 message>
        Allow to clear messages of user who have this role.
        """
        def delete_role(m):
            return role.id in [r.id for r in m.author.roles]
        try:
            counter =await self.bot.purge_from(ctx.message.channel,limit=limit,check=delete_role)
            await self.bot.say("```py\nClean up message: {} from {}\n```".format(len(counter),role.name))

        except:
            pass

    @clean.command(brief="Allow to clear that user's message", pass_context=True, invoke_without_command=True)
    @commands.check(is_enable)
    @commands.check(check_roles)
    @commands.bot_has_permissions(manage_messages=True)
    async def person(self,ctx,user: discord.Member,*,limit: int = 100):
        """
        <prefix> person <which person> <optional, but how many, default 100 message>
        Allow to clear message of certain person.
        """
        def delete_player(m):
                return m.author.id == user.id
        counter = await self.bot.purge_from(ctx.message.channel,check=delete_player,limit=limit)
        await self.bot.say("```py\nI have clean {} message from {}```".format(len(counter),user.name))

    @clean.command(brief="Allow to clear all message", pass_context=True, invoke_without_command=True)
    @commands.check(is_enable)
    @commands.check(check_roles)
    @commands.bot_has_permissions(manage_messages=True)
    async def all(self,ctx,*,limit: int=100):
        """
        <prefix> all <optional but how many, default 100 message>
        Allow to clear all message, nothing can stop it.
        """
        counter = await self.bot.purge_from(ctx.message.channel,limit=limit)
        await self.bot.say_edit("```py\nI have clean {}```".format(len(counter)))


#############################################################
#    _  __  _          _          __  ____                  #
#   | |/ / (_)        | |        / / |  _ \                 #
#   | ' /   _    ___  | | __    / /  | |_) |   __ _   _ __  #
#   |  <   | |  / __| | |/ /   / /   |  _ <   / _` | | '_ \ #
#   | . \  | | | (__  |   <   / /    | |_) | | (_| | | | | |#
#   |_|\_\ |_|  \___| |_|\_\ /_/     |____/   \__,_| |_| |_|#
#############################################################

    @commands.command(brief="Allow to kick user")
    @commands.check(is_enable)
    @commands.check(check_roles)
    @commands.bot_has_permissions( kick_members=True)
    async def kick(self,user:discord.Member):
        """
        <prefix> kick <user name>

        Use mention is faster way to get user.
        Allow to kick user from server.
        """
        await self.bot.kick(user)
        await self.bot.says_edit("I have kicked {}".format(user.name))

    @commands.command(brief="Allow to ban user")
    @commands.check(is_enable)
    @commands.check(check_roles)
    @commands.bot_has_permissions( ban_members=True)
    async def ban(self,user:discord.Member,*,day : int = 1):
        """
       <prefix> ban <user name> <optional but how many day, default is 1 day for delete messages>

        Use mention is faster way to get user.
        Allow to ban user from server, default day of delete message is 1 day.

        """
        await self.bot.ban(user,delete_message_days=day)
        await self.bot.says_edit("I have ban {}".format(user.name))

    @commands.command(brief="Allow to softban user which is equal to kick and delete its message")
    @commands.check(is_enable)
    @commands.check(check_roles)
    @commands.bot_has_permissions( ban_members=True)
    async def softban(self,user:discord.Member,*,day : int = 1):
        """
        <prefix> softban <user name> <optional but how many day to delete message, default is 1>

        This is just kick + delete message,
        allow to kick user and have delete message.
        """
        await self.bot.ban(user,delete_message_days = day)
        await self.bot.unban(user.server,user)
        await self.bot.says_edit("I have softban {}".format(user.name))


#################################
#    _____            _         #
#   |  __ \          | |        #
#   | |__) |   ___   | |   ___  #
#   |  _  /   / _ \  | |  / _ \ #
#   | | \ \  | (_) | | | |  __/ #
#   |_|  \_\  \___/  |_|  \___| #
#################################

    @commands.group(brief="Multi subcommand related to role",invoke_without_command=True)
    @commands.check(is_enable)
    @commands.check(check_roles)
    @commands.bot_has_permissions(manage_roles=True)
    async def role(self):
        """
        A subcommand of it.
        do this
        <prefix> help role
        to see a more infomations of its sub commands
        """
        return

    @role.command(brief="allow to add role to that user")
    @commands.check(is_enable)
    @commands.check(check_roles)
    @commands.bot_has_permissions(manage_roles=True)
    async def add(self,user:discord.Member,*role:discord.Role):
        """
        <prefix> add <user name> <which role>
        Allow to add role to member, helpful for people who is on phone.
        Also you can add multi role to members at same time
        """
        await self.bot.add_roles(user,*role)
        await self.bot.says_edit("Added a role to {}".format(user.name))

    @role.command(brief="allow to remove role from that user")
    @commands.check(is_enable)
    @commands.check(check_roles)
    @commands.bot_has_permissions(manage_roles=True)
    async def remove(self,user:discord.Member,*role:discord.Role):
        """
        <prefix> remove <user name> <which role>
        Allow to remove role form that member, helpful for people who is on phone.
        Also you can remove multi role from member at same time.
        """
        await self.bot.remove_roles(user,*role)
        await self.bot.says_edit("Remove role from {}".format(user.name))

def setup(bot):
    bot.add_cog(Mod(bot))