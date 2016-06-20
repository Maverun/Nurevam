from discord.ext import commands
from .utils import utils
import asyncio
import discord

def check_roles(msg):
    Admin = utils.check_roles(msg, "Mod", "admin_roles")
    return Admin

def is_enable(msg): #Checking if cogs' config for this server is off or not
    return utils.is_enable(msg, "mod")

class Mod():
    """
    A Mod tools for Mod.
    """
    def __init__(self, bot):
        self.bot = bot
        self.bot.say_edit = bot.says_edit

    def delete_mine(self,m):
        return m.author == self.bot.user

    @commands.group(name="clean",brief="Allow to clean bot itself",pass_context=True,invoke_without_command=True)
    @commands.check(is_enable)
    @commands.check(check_roles)
    async def cleanup(self,ctx,*,limit:int=100):
        counter = 0
        if ctx.message.channel.is_private:
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


    @cleanup.command(name="role",pass_context=True,invoke_without_command=True)
    @commands.check(is_enable)
    @commands.check(check_roles)
    async def roles(self,ctx,role : discord.Role,*,limit: int=100):
        def delete_role(m):
            return role.id in [r.id for r in m.author.roles]
        try:
            counter =await self.bot.purge_from(ctx.message.channel,limit=limit,check=delete_role)
            await self.bot.say("```py\nClean up message: {} from {}\n```".format(len(counter),role.name))

        except:
            pass

    @cleanup.command(name="person",brief="Allow to clear that user's message",pass_context=True,invoke_without_command=True)
    @commands.check(is_enable)
    @commands.check(check_roles)
    async def person(self,ctx,user: discord.Member,*,limit: int = 100):
        def delete_player(m):
                return m.author.id == user.id
        counter = await self.bot.purge_from(ctx.message.channel,check=delete_player,limit=limit)
        await self.bot.say("```py\nI have clean {} message from {}```".format(len(counter),user.name))

    @cleanup.command(name="all",brief="Allow to clear all message",pass_context=True,invoke_without_command=True)
    @commands.check(is_enable)
    @commands.check(check_roles)
    async def all(self,ctx,*,limit: int=100):
        counter = await self.bot.purge_from(ctx.message.channel,limit=limit)
        await self.bot.say_edit("```py\nI have clean {}```".format(len(counter)))

def setup(bot):
    bot.add_cog(Mod(bot))