from discord.ext import commands
from .Utils import Read
import asyncio
import discord

def Setup(): #Rerun those for refresh variables when reload
    global Config
    global Roles
    global Command
    global Com_Role
    Config= Read.config
    Roles = Read.Bot_Config["Roles"]
    Command= Read.Bot_Config["Cogs"]
    Com_Role=Read.Bot_Config



class Mod():
    """
    A Mod tools for Mod.
    """
    def __init__(self, bot):
        self.bot = bot
        Setup()

    @commands.group(name="clean",brief="Allow to clean bot itself",pass_context=True,invoke_without_command=True)
    async def cleanup(self,ctx):
        counter = 0
        async for message in self.bot.logs_from(ctx.message.channel,limit=100):
            if self.bot.user.id == message.author.id:
                await self.bot.delete_message(message)
                counter +=1
        await self.bot.say("```py\nClean up message: {}\n```".format(counter))


    @cleanup.command(name="roles",pass_context=True,invoke_without_command=True)
    async def roles(self,ctx,*,name :str):
        print(name)
        role = discord.utils.get(ctx.message.server.roles, name=name)
        if ctx.message.author.id == "105853969175212032":
            counter = 0
            found = False
            async for message in self.bot.logs_from(ctx.message.channel,limit=20):
                print(message.author.name)
                if role in ctx.message.author.roles:
                    found=True
                    await self.bot.delete_message(message)
                    counter +=1
            if found:
                await self.bot.say("```py\nI cleaned {} message from the  {} role```".format(counter,name))
            else:
                await self.bot.say("I could not find this role! Please try again.")


    @cleanup.command(name="person",brief="Allow to clear that user's message",pass_context=True,invoke_without_command=True)
    async def person(self,ctx):
        if ctx.message.author.id == "105853969175212032":
            name = ctx.message.mentions[0]

            print(name)
            counter = 0
            async for message in self.bot.logs_from(ctx.message.channel,limit=10):
                if message.author.id == name.id:
                    await self.bot.delete_message(message)
                    counter +=1
            await self.bot.say("```py\nI cleaned {} message from {}```".format(counter,name))


def setup(bot):
    bot.add_cog(Mod(bot))