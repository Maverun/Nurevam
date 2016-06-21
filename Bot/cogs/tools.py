from discord.ext import commands
from .utils import utils
import glob
import discord
import asyncio
import traceback
import datetime
import inspect


def list_cogs(): #Check a list and load it
    cogs = glob.glob("cogs/*.py")
    clean = []
    for c in cogs:
        c = c.replace("/", "\\") # Linux fix
        if "__init__" in c:
            continue
        clean.append("cogs." + c.split("\\")[1].replace(".py", ""))
    return clean

class Tools():
    """
    A Tools that is only for owner to control bots
    Such as reload/load/unload cogs(plugins)
    """
    def __init__(self, bot):
        self.bot = bot
        self.redis = bot.db.redis
        self.bot.say_edit = bot.says_edit
        asyncio.get_event_loop().create_task(self.timer_update())


    #Load/Unload/Reload cogs
    @commands.command(hidden=True)
    @commands.check(utils.is_owner)
    async def load(self,*, module : str):
        """Loads a module
        Example: load cogs.mod"""
        module ="cogs."+module.strip()
        if not module in list_cogs():
            await self.bot.say("{} doesn't exist.".format(module))
            return
        try:
            self.bot.load_extension(module)
        except Exception as e:
            await self.bot.say('{}: {}'.format(type(e).__name__, e))
            raise
        else:
            await self.bot.say("Enabled.".format(module))

    @commands.command(hidden=True)
    @commands.check(utils.is_owner)
    async def unload(self,*, module : str):
        """Unloads a module
        Example: unload cogs.mod"""
        module ="cogs."+module.strip()
        if not module in list_cogs():
            await self.bot.say("That module doesn't exist.")
            return
        try:
            self.bot.unload_extension(module)
        except Exception as e:
            await self.bot.say('{}: {}'.format(type(e).__name__, e))
        else:
            await self.bot.say("Module disabled.")

    @commands.command(name="reload",hidden=True)
    @commands.check(utils.is_owner)
    async def _reload(self,*, module : str):
        """Reloads a module
        Example: reload cogs.mod"""
        module ="cogs."+module.strip()
        if not module in list_cogs():
            await self.bot.say("This module doesn't exist.".format(module))
            return
        try:
            self.bot.unload_extension(module)
            self.bot.load_extension(module)
        except Exception as e:
            await self.bot.say('\U0001f52b')
            await self.bot.say('{}: {}'.format(type(e).__name__, e))
            raise
        else:
            await self.bot.say("Module reloaded.")

    @commands.command(name="reload-all",hidden=True)
    @commands.check(utils.is_owner)
    async def reload_all(self):
        """Reload all modules"""
        cogs = list_cogs()
        for cog in cogs:
            try:
                self.bot.unload_extension(cog)
                self.bot.load_extension(cog)
                print ("Load {}".format(cog))
            except Exception as e:
                print(e)
                raise    #Load/Unload/Reload cogs
        await self.bot.say("```fix\n{}\nhas been reload\n```".format("\n".join(cogs)))


    @commands.command(pass_context=True, hidden=True)
    @commands.check(utils.is_owner)
    async def debug(self, ctx, *, code : str):
        """Evaluates code."""
        code = code.strip('` ')
        python = '```py\n{}\n```'
        result = None

        env = {
            'bot': self.bot,
            'ctx': ctx,
            'message': ctx.message,
            'server': ctx.message.server,
            'channel': ctx.message.channel,
            'author': ctx.message.author
        }

        env.update(globals())

        try:
            result = eval(code, env)
            if inspect.isawaitable(result):
                result = await result
        except Exception as e:
            await self.bot.say(python.format(type(e).__name__ + ': ' + str(e)))
            return

        await self.bot.say(python.format(result))

    @commands.command(name="server",pass_context=True,hidden=True)
    @commands.check(utils.is_owner)
    async def Check_Server(self,ctx):
        cogs = list_cogs()
        print(cogs)
        # list = await self.redis.keys()
        server = self.bot.servers
        await self.redis.set("Info:Total Server",len(server))
        for name in server:
            print(name)
            await self.redis.hset("Info:Server",str(name.id),str(name))
            print(name.id)
            #Server setting
            await self.redis.hmset("{}:Config:Delete_MSG".format(name.id),"core","off")

    @commands.command(name="enable",pass_context=True,hidden=True)
    @commands.check(utils.is_owner)
    async def Enable(self,ctx,*,Cogs):
        print(Cogs)
        check = await self.redis.hget("{}:Config:cogs".format(ctx.message.server.id),Cogs)
        if check == "off":
            await self.redis.hset("{}:Config:cogs".format(ctx.message.server.id),Cogs,"on")
            await self.bot.say("Update.")
        elif check == "on":
            await self.bot.say("It is already enable.")

    @commands.command(name="disable",pass_context=True,hidden=True)
    @commands.check(utils.is_owner)
    async def Disable(self,ctx,*,Cogs):
        print(Cogs)
        check = await self.redis.hget("{}:Config:cogs".format(ctx.message.server.id),Cogs)
        if check == "on":
            await self.redis.hset("{}:Config:cogs".format(ctx.message.server.id),Cogs,"off")
            await self.bot.say("Update.")
        elif check == "off":
            await self.bot.say("It is already disable.")

    @commands.command(name="RESET",pass_context=True,hidden=True)
    @commands.check(utils.is_owner)
    async def RESET(self,ctx):
        await self.bot.say("```diff\n-WARNING! DOING THIS WILL COMPLETE RESET ALL DATABASE! ARE YOU SURE!?-\n```")
        answer = await self.bot.wait_for_message(timeout=5,author=ctx.message.author)
        if answer.content =="YES":
            await self.redis.flushall()
            await self.bot.say("RESET.")
        else:
            print("SMITH")
            return

    @commands.command(name="get-all-icon-name",pass_context=True,hidden=True)
    @commands.check(utils.is_owner)
    async def get_all(self,ctx):
        info = await self.update_all()
        await self.bot.say("Collect {}".format(info))

    async def update_all(self):
        info = set(self.bot.get_all_members())
        for data in info:
            if data.avatar != None:
                await self.redis.hset("Info:Icon",data.id,data.avatar)
            await self.redis.hset("Info:Name",data.id,data.name)
        current_Time = datetime.datetime.utcnow().strftime("%b/%d/%Y %H:%M:%S UTC")
        utils.prCyan("{}: Update {} of icon,name!".format(current_Time,len(info)))
        server = self.bot.servers
        for x in server:
            if x.icon != None:
                await self.redis.hset("Info:Server_Icon",x.id,x.icon)
            await self.redis.hset("Info:Server",x.id,x.name)
        return len(info)

    async def timer_update(self):
        while True:
            await self.update_all()
            await asyncio.sleep(3600)

    @commands.command(name="List-server",hidden=True)
    @commands.check(utils.is_owner)
    async def list_server(self):
        info = [r.name for r in self.bot.servers]
        for server in self.bot.servers:
            name = str(server)
            owner = str(server.owner.name)
            print("Server:{0:<{first}}\tOwner: {1}".format(name,owner,first=len(max(info,key=len))))

    @commands.command(hidden=True,pass_context=True)
    @commands.check(utils.is_owner)
    async def acivity(self,ctx):
        server = ctx.message.server.id
        player_data = await  self.redis.sort("{}:Level:Player".format(server),"{}:Level:Player:*->Name".format(server),
                                                                     "{}:Level:Player:*->Total Message Count".format(server),
                                                                     by="{}:Level:Player:*->Total Message Count".format(server),offset=0,count=-1)
        player_data = list(reversed(player_data))
        msg=[]
        for x in range(0,len(player_data),2):
            msg.append("{},{}\n".format(player_data[x+1],player_data[x]))
        with open("acivity.txt","w",encoding='utf-8') as f:
            for x in msg:
                print(x)
                f.write(x)
        with open("acivity.txt","rb") as r:
            await self.bot.upload(r)

def setup(bot):
    bot.add_cog(Tools(bot))

