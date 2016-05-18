from discord.ext import commands
from .utils import utils
import asyncio
import discord


class Mod():
    """
    A Mod tools for Mod.
    """
    def __init__(self, bot):
        self.bot = bot

    def delete_mine(self,m):
        return m.author == self.bot.user

    @commands.group(name="clean",brief="Allow to clean bot itself",pass_context=True,invoke_without_command=True)
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
                await self.bot.say("```py\nI have clean {} message from role call {}```".format(counter,name))
            else:
                await self.bot.say("I cannot find that roles! Please try again.")


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
            await self.bot.say("```py\nI have clean {} message from {}```".format(counter,name))


def setup(bot):
    bot.add_cog(Mod(bot))