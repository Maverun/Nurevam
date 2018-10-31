from discord.ext import commands
from .utils import utils
import datetime
import asyncio
import discord
import logging

log = logging.getLogger(__name__)

def check_roles(ctx):
    if ctx.message.author.id == 105853969175212032:
        return True
    return utils.check_roles(ctx, "Mod", "admin_roles")



class get_person(commands.MemberConverter):
    def __init__(self, *, lower=False):
        self.lower = lower
        super().__init__()





class Mod():
    """
    A mod tool for Mods.
    """
    def __init__(self, bot):
        self.bot = bot
        self.redis = bot.db.redis
        self.bot.say_edit = bot.say

    def __local_check(self,ctx):
        return utils.is_enable(ctx,"mod") or ctx.message.author.id == self.bot.owner.id

    def delete_mine(self,m):
        return m.author.id == self.bot.user.id

#########################################
#     _____   _                         #
#    / ____| | |                        #
#   | |      | |   ___    __ _   _ __   #
#   | |      | |  / _ \  / _` | | '_ \  #
#   | |____  | | |  __/ | (_| | | | | | #
#    \_____| |_|  \___|  \__,_| |_| |_| #
#########################################

    @commands.group(brief="Allow to clean bot itself, have subcommand",invoke_without_command=True)
    @commands.check(check_roles)
    # async def clean(self, ctx, *, limit:int=100):
    async def clean(self, ctx,limit:int = 100,user:commands.MemberConverter or bool = False,):
        """
        Is able to clear up it's own messages.
        can affect any user's messages by mention it.
        """
        if limit > 2000:
            return await self.bot.say(ctx,content = "Won't able to delete due to {limit}/2000 message to delete.".format(limit = limit))
        if user:
            counter = await ctx.message.channel.purge(check=lambda m:m.author.id == user.id,limit=limit)
            await self.bot.say(ctx,content = "```py\nI cleared {} posts from {}```".format(len(counter),user.name))
        else:
            counter = await ctx.message.channel.purge(limit = limit,check=self.delete_mine)
            await self.bot.say(ctx,content = "```py\nI cleared {} posts of mine\n```".format(len(counter)))


    @clean.command(brief= "Is able to clear a certain role's messages",pass_context=True, invoke_without_command=True)
    @commands.check(check_roles)
    @commands.bot_has_permissions(manage_messages=True)
    async def role(self,ctx,roles : discord.Role,limit : int=100):
        """
        <prefix> role <the role> <optional, number of messages, default: 100>
        Is able to clear messages of all users who have this role.
        """
        def delete_role(m):
            print(m.author)
            return roles.id in [r.id for r in m.author.roles]
        counter =await ctx.message.channel.purge(limit=limit,check=delete_role)
        await self.bot.say(ctx, content = "```py\nI cleared {} from person who have role of {}\n```".format(len(counter),roles.name))

    @clean.command(brief="Is able to clear a certain user's messages",invoke_without_command=True)
    @commands.check(check_roles)
    @commands.bot_has_permissions(manage_messages=True)
    async def person(self,ctx,user: discord.Member,*,limit: int = 100):
        """
        <prefix> person <the person> <optional, number of messages, default 100>
        Is able to clear the messages of a certain person.
        """
        def delete_player(m):
                return m.author.id == user.id
        counter = await ctx.message.channel.purge(check=delete_player,limit=limit)
        await self.bot.say(ctx,content = "```py\nI cleared {} posts from {}```".format(len(counter),user.name))

    @clean.command(name = "all",brief="Allow to clear all message", invoke_without_command=True)
    @commands.check(check_roles)
    @commands.bot_has_permissions(manage_messages=True)
    async def _all(self,ctx,*,limit: int=100):
        """
        <prefix> all <optional but how many, default 100 message>
        Allow to clear all message, nothing can stop it.
        """
        counter = await ctx.message.channel.purge(limit =limit)
        await self.bot.say(ctx,content = "```py\nI cleared {} posts```".format(len(counter)))


#############################################################
#    _  __  _          _          __  ____                  #
#   | |/ / (_)        | |        / / |  _ \                 #
#   | ' /   _    ___  | | __    / /  | |_) |   __ _   _ __  #
#   |  <   | |  / __| | |/ /   / /   |  _ <   / _` | | '_ \ #
#   | . \  | | | (__  |   <   / /    | |_) | | (_| | | | | |#
#   |_|\_\ |_|  \___| |_|\_\ /_/     |____/   \__,_| |_| |_|#
#############################################################
    def format_reason(self,ctx,reason):
        if reason is None:
            reason = "Request by {}".format(ctx.message.author)
        else:
            reason += " Request by {}".format(ctx.message.author)
        return reason

    @commands.command(brief="Is able to kick a user")
    @commands.check(check_roles)
    @commands.bot_has_permissions(kick_members=True)
    async def kick(self,ctx,user:discord.Member,*,reason:str = None):
        """
        <prefix> kick <user name>
        Mentioning is a faster way to get the user.
        Is able to kick a user from guild.
        """
        await ctx.message.guild.kick(user,reason = self.format_reason(ctx,reason))
        await self.bot.say(ctx,content = "I have kicked {}".format(user.name))

    @commands.command(brief="Is able to ban a user")
    @commands.check(check_roles)
    @commands.bot_has_permissions( ban_members=True)
    async def ban(self,ctx,user:discord.Member,*,reason:str = None):
        """
        <prefix> ban <user name> <optional, number of passed days, for which the user's messages are deleted, default 1>
        Mentioning is a faster way to get the user.
        Is able to ban a user from the guild, default number of passed days, for which messages are deleted, is 1.
        """
        await ctx.message.guild.ban(user,reason = self.format_reason(ctx,reason))
        await self.bot.say(ctx,content = "I have banned {}".format(user.name))

    @commands.command(brief="Is able to softban a user which is equal to kicking him and deleting his messages")
    @commands.check(check_roles)
    @commands.bot_has_permissions( ban_members=True)
    async def softban(self,ctx,user:discord.Member,*,reason:str = None):
        """
        <prefix> softban <user name> <optional, number of passed days, for which the messages are deleted, default is 1>
        This is just kicking + deleting messages,
        Is able to kick a user and delete his messages.
        """
        await ctx.message.guild.ban(user,reason = self.format_reason(ctx,reason))
        await ctx.message.guild.unban(user)
        await self.bot.say(ctx,content = "I have softbanned {}".format(user.name))


#################################
#    _____            _         #
#   |  __ \          | |        #
#   | |__) |   ___   | |   ___  #
#   |  _  /   / _ \  | |  / _ \ #
#   | | \ \  | (_) | | | |  __/ #
#   |_|  \_\  \___/  |_|  \___| #
#################################

    @commands.group(name = "role",brief="Multi subcommand related to role",invoke_without_command=True)
    @commands.check(check_roles)
    @commands.bot_has_permissions(manage_roles=True)
    async def _role(self):
        """
        A subcommand of it.
        do this
        <prefix> help role
        to see a more infomations of its sub commands
        """
        return

    @_role.command(brief="Is able to add a role to a user")
    @commands.check(check_roles)
    @commands.bot_has_permissions(manage_roles=True)
    async def add(self,ctx,user:discord.Member,*role:discord.Role):
        """
        <prefix> add <user name> <the role>
        Is able to add a role to a member, this is useful for people who are on phone.
        You can also add multiple roles to a member at the same time.
        """
        await user.add_roles(user,*role,reason = "Request by {}".format(ctx.message.author))
        await self.bot.say(ctx,content = "Added a role to {}".format(user.name))

    @_role.command(brief="Is able to remove a role from a user")
    @commands.check(check_roles)
    @commands.bot_has_permissions(manage_roles=True)
    async def remove(self,ctx,user:discord.Member,*role:discord.Role):
        """
        <prefix> remove <user name> <the role>
        Is able to remove a role from a member, this is useful for people who are on phone.
        You can also remove multiple roles from a member at the same time.
        """
        await user.remove_roles(user,*role,reason ="Request by {}".format(ctx.message.author))
        await self.bot.say(ctx,content = "Remove role from {}".format(user.name))


def setup(bot):
    bot.add_cog(Mod(bot))