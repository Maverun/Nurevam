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
    A mod tool for Mods.
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

    @commands.group(brief="Clears the bot's messages",pass_context=True,invoke_without_command=True)
    @commands.check(is_enable)
    @commands.check(check_roles)
    async def clean(self, ctx, *, limit:int=100):
        """
        Clears it's own messages.
        Does not affect any user's messages.
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
        await self.bot.say("```py\nDeleted {} messages\n```".format(counter))

    @clean.command(brief= "Clears a certain role's messages",pass_context=True, invoke_without_command=True)
    @commands.check(is_enable)
    @commands.check(check_roles)
    @commands.bot_has_permissions(manage_messages=True)
    async def role(self,ctx,roles : discord.Role,limit : int=100):
        """
        <prefix> role <the role> <optional, number of messages, default: 100>
        Clears the messages of all users who have this role.
        """
        def delete_role(m):
            return roles.id in [r.id for r in m.author.roles]
        try:
            counter =await self.bot.purge_from(ctx.message.channel,limit=limit,check=delete_role)
            await self.bot.say("```py\nDeleted {} messages from {}\n```".format(len(counter),roles.name))
        except:
            pass

    @clean.command(brief="Clears a certain user's messages", pass_context=True, invoke_without_command=True)
    @commands.check(is_enable)
    @commands.check(check_roles)
    @commands.bot_has_permissions(manage_messages=True)
    async def person(self,ctx,user: discord.Member,*,limit: int = 100):
        """
        <prefix> person <the person> <optional, number of messages, default 100>
        Clears the messages of a certain person.
        """
        def delete_player(m):
                return m.author.id == user.id
        counter = await self.bot.purge_from(ctx.message.channel,check=delete_player,limit=limit)
        await self.bot.say("```py\nDeleted {} messages from {}```".format(len(counter),user.name))

    @clean.command(brief="Clears all messages", pass_context=True, invoke_without_command=True)
    @commands.check(is_enable)
    @commands.check(check_roles)
    @commands.bot_has_permissions(manage_messages=True)
    async def all(self,ctx,*,limit: int=100):
        """
        <prefix> all <optional, number of messages, default 100>
        Clears all messages, nothing can stop it.
        """
        counter = await self.bot.purge_from(ctx.message.channel,limit=limit)
        await self.bot.say_edit("```py\nDeleted {} messages```".format(len(counter)))


#############################################################
#    _  __  _          _          __  ____                  #
#   | |/ / (_)        | |        / / |  _ \                 #
#   | ' /   _    ___  | | __    / /  | |_) |   __ _   _ __  #
#   |  <   | |  / __| | |/ /   / /   |  _ <   / _` | | '_ \ #
#   | . \  | | | (__  |   <   / /    | |_) | | (_| | | | | |#
#   |_|\_\ |_|  \___| |_|\_\ /_/     |____/   \__,_| |_| |_|#
#############################################################

    @commands.command(brief="Kicks a user")
    @commands.check(is_enable)
    @commands.check(check_roles)
    @commands.bot_has_permissions( kick_members=True)
    async def kick(self,user:discord.Member):
        """
        <prefix> kick <user name>

        Mentioning is a faster way to get the user.
        Kicks a user from the server.
        """
        await self.bot.kick(user)
        await self.bot.says_edit("I have kicked {}".format(user.name))

    @commands.command(brief="Bans a user")
    @commands.check(is_enable)
    @commands.check(check_roles)
    @commands.bot_has_permissions( ban_members=True)
    async def ban(self,user:discord.Member,*,day : int = 1):
        """
       <prefix> ban <user name> <optional, number of passed days, for which the user's messages are deleted, default 1>

        Mentioning is a faster way to get the user.
        Bans a user from the server, default number of passed days, for which messages are deleted, is 1.

        """
        await self.bot.ban(user,delete_message_days=day)
        await self.bot.says_edit("I have banned {}".format(user.name))

    @commands.command(brief="ISoftbans a user which is equal to kicking him and deleteting his messages")
    @commands.check(is_enable)
    @commands.check(check_roles)
    @commands.bot_has_permissions( ban_members=True)
    async def softban(self,user:discord.Member,*,day : int = 1):
        """
        <prefix> softban <user name> <optional, number of passed days, for which the messages are deleted, default is 1>

        This is just kicking + deleteting messages,
        Kicks a user and deletes his messages.
        """
        await self.bot.ban(user,delete_message_days = day)
        await self.bot.unban(user.server,user)
        await self.bot.says_edit("I have softbanned {}".format(user.name))


#################################
#    _____            _         #
#   |  __ \          | |        #
#   | |__) |   ___   | |   ___  #
#   |  _  /   / _ \  | |  / _ \ #
#   | | \ \  | (_) | | | |  __/ #
#   |_|  \_\  \___/  |_|  \___| #
#################################

    @commands.group(brief="Command related to rles",invoke_without_command=True)
    @commands.check(is_enable)
    @commands.check(check_roles)
    @commands.bot_has_permissions(manage_roles=True)
    async def role(self):
        """
        Works with subcommands.
        Do <prefix> help role
        to see more about the subcommands.
        """
        return

    @role.command(brief="Adds a role to a user")
    @commands.check(is_enable)
    @commands.check(check_roles)
    @commands.bot_has_permissions(manage_roles=True)
    async def add(self,user:discord.Member,*role:discord.Role):
        """
        <prefix> add <user name> <the role>
        Adds a role to a member; this is useful for people on the phone.
        You can also add multiple roles to a member at the same time.
        """
        await self.bot.add_roles(user,*role)
        await self.bot.says_edit("I added a role to {}".format(user.name))

    @role.command(brief="Removes a role from a user")
    @commands.check(is_enable)
    @commands.check(check_roles)
    @commands.bot_has_permissions(manage_roles=True)
    async def remove(self,user:discord.Member,*role:discord.Role):
        """
        <prefix> remove <user name> <the role>
        Is able to remove a role from a member, this is useful for people on the phone.
        You can also remove multiple roles from a member at the same time.
        """
        await self.bot.remove_roles(user,*role)
        await self.bot.says_edit("I removed a role from {}".format(user.name))

def setup(bot):
    bot.add_cog(Mod(bot))
