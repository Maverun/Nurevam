from discord.ext import commands
from .utils import utils
import asyncio
import discord
import datetime

def check_roles(ctx):
    print(ctx)
    if ctx.message.author.id == 105853969175212032:
        return True
    admin = utils.check_roles(ctx, "Mod", "admin_roles")
    print(admin)
    print("uh ok")
    return admin

class Mod():
    """
    A mod tool for Mods.
    """
    def __init__(self, bot):
        self.bot = bot
        self.bot.say_edit = bot.say

    def __local_check(self,ctx):
        return utils.is_enable(ctx,"mod")

    def delete_mine(self,m):
        return m.author.id == self.bot.user.id

    async def on_member_join(self,member): #this is only temp patch for friend of mine...
        if member.guild.id == 241901242220150784:
            created = member.created_at
            current = datetime.datetime.utcnow()
            age = current - created
            print(age)
            if int(age.total_seconds()) <= 600:
                print("Yes ban this one")
                await member.ban()

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
    async def clean(self, ctx, *, limit:int=100):
        """
        Is able to clear up it's own messages.
        Does not affect any user's messages.
        """
        counter = await ctx.message.channel.purge(limit = limit,check=self.delete_mine)
        await self.bot.say(ctx,content = "```py\nClean up message: {}\n```".format(len(counter)))

    @clean.command(brief= "Is able to clear a certain role's messages",pass_context=True, invoke_without_command=True)
    @commands.check(check_roles)
    @commands.bot_has_permissions(manage_messages=True)
    async def role(self,ctx,roles : discord.Role,limit : int=100):
        """
        <prefix> role <the role> <optional, number of messages, default: 100>
        Is able to clear messages of all users who have this role.
        """
        print("over here")
        def delete_role(m):
            print(m.author)
            return roles.id in [r.id for r in m.author.roles]
        counter =await ctx.message.channel.purge(limit=limit,check=delete_role)
        await self.bot.say(ctx, content = "```py\nClean up message: {} from {}\n```".format(len(counter),roles.name))

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
        await self.bot.say(ctx,content = "```py\nI have clean {} message from {}```".format(len(counter),user.name))

    @clean.command(name = "all",brief="Allow to clear all message", invoke_without_command=True)
    @commands.check(check_roles)
    @commands.bot_has_permissions(manage_messages=True)
    async def _all(self,ctx,*,limit: int=100):
        """
        <prefix> all <optional but how many, default 100 message>
        Allow to clear all message, nothing can stop it.
        """
        counter = await ctx.message.channel.purge(limit =limit)
        await self.bot.say(ctx,content = "```py\nI have clean {}```".format(len(counter)))


#############################################################
#    _  __  _          _          __  ____                  #
#   | |/ / (_)        | |        / / |  _ \                 #
#   | ' /   _    ___  | | __    / /  | |_) |   __ _   _ __  #
#   |  <   | |  / __| | |/ /   / /   |  _ <   / _` | | '_ \ #
#   | . \  | | | (__  |   <   / /    | |_) | | (_| | | | | |#
#   |_|\_\ |_|  \___| |_|\_\ /_/     |____/   \__,_| |_| |_|#
#############################################################

    @commands.command(brief="Is able to kick a user")
    @commands.check(check_roles)
    @commands.bot_has_permissions(kick_members=True)
    async def kick(self,ctx,user:discord.Member):
        """
        <prefix> kick <user name>

        Mentioning is a faster way to get the user.
        Is able to kick a user from guild.
        """
        await ctx.message.guild.kick(user)
        await self.bot.say(ctx,content = "I have kicked {}".format(user.name))

    @commands.command(brief="Is able to ban a user")
    @commands.check(check_roles)
    @commands.bot_has_permissions( ban_members=True)
    async def ban(self,ctx,user:discord.Member,*,day : int = 1):
        """
        <prefix> ban <user name> <optional, number of passed days, for which the user's messages are deleted, default 1>
        Mentioning is a faster way to get the user.
        Is able to ban a user from the guild, default number of passed days, for which messages are deleted, is 1.
        """
        await ctx.message.guild.ban(user,delete_message_days=day)
        await self.bot.say(ctx,content = "I have banned  {}".format(user.name))

    @commands.command(brief="Is able to softban a user which is equal to kicking him and deleting his messages")
    @commands.check(check_roles)
    @commands.bot_has_permissions( ban_members=True)
    async def softban(self,ctx,user:discord.Member,*,day : int = 1):
        """
        <prefix> softban <user name> <optional, number of passed days, for which the messages are deleted, default is 1>
        This is just kicking + deleting messages,
        Is able to kick a user and delete his messages.
        """
        await ctx.message.guild.ban(user,delete_message_days = day)
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
        await user.add_roles(user,*role)
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
        await user.remove_roles(user,*role)
        await self.bot.say(ctx,content = "Remove role from {}".format(user.name))

def setup(bot):
    bot.add_cog(Mod(bot))
