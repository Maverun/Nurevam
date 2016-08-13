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
        self.update_info = None
        self.back_up_info = None
        self.counter = 0
        asyncio.get_event_loop().create_task(self.timer_update())
        asyncio.get_event_loop().create_task(self.update_check_loop())


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
        if self.update_info:
            utils.prCyan(self.update_info)
        await self.update_check()
        server = list(self.bot.servers)
        for x in server:
            if x.icon != None:
                await self.redis.hset("Info:Server_Icon",x.id,x.icon)
            await self.redis.hset("Info:Server",x.id,x.name)
        return len(info)

    async def timer_update(self):
        while True:
            await self.update_all()
            await asyncio.sleep(3600)

    @commands.command(name="list-server",hidden=True)
    @commands.check(utils.is_owner)
    async def list_server(self):
        info = [r.name for r in self.bot.servers]
        char_name = [str(r.owner) for r in self.bot.servers]
        for server in self.bot.servers:
            name = str(server)
            server_id = str(server.id)
            owner = str(server.owner)
            total =  server.member_count
            print("Server: {0:<{first}}[{1}]\tOwner: {2:<{second}}\t Member Count: {3}".format(name,server_id,owner,total,
                                                                                               first=len(max(info,key=len)),
                                                                                               second = len(max(char_name,key=len))))

    @commands.command(hidden=True,pass_context=True)
    @commands.check(utils.is_owner)
    async def activity(self,ctx):
        server = ctx.message.server.id
        player_data = await  self.redis.sort("{}:Level:Player".format(server),
                                                                     "{}:Level:Player:*->Name".format(server),
                                                                     "{}:Level:Player:*->Total Message Count".format(server),
                                                                     "{}:Level:Player:*->ID".format(server),
                                                                     by="{}:Level:Player:*->Total Message Count".format(server),offset=0,count=-1)
        player_data = list(reversed(player_data))
        msg=[]
        print(player_data)
        for x in range(0,len(player_data),3):
            msg.append("{},{},{}\n".format(player_data[x],player_data[x+2].replace(","," "),player_data[x+1]))
        with open("acivity.txt","w",encoding='utf-8') as f:
            for x in msg:
                print(x)
                f.write(x)
        with open("acivity.txt","rb") as r:
            await self.bot.upload(r)

    @commands.command(hidden=True)
    @commands.check(utils.is_owner)
    async def update(self):
        data = self.bot.background
        now  = datetime.datetime.now()
        info = []
        for x in data:
            c = now - data[x]
            time = divmod(c.days * 86400 + c.seconds,60)
            minutes = time[0]
            second = time[1]
            info.append("{}: {} min, {} second".format(x,minutes,second))
        await self.bot.say("```xl\n{}\n```".format("\n".join(info)))

    async def update_check(self):
        data = self.bot.background
        now = datetime.datetime.now()
        info = []
        failed = []
        failed_boolean = False
        for x in data:
            c = now - data[x]
            time = divmod(c.days * 86400 + c.seconds, 60)
            minutes = time[0]
            second = time[1]
            if minutes >= 1:
                failed.append("-{}: {} min, {} second".format(x, minutes, second))
                self.bot.unload_extension("cogs.{}".format(x))
                self.bot.load_extension("cogs.{}".format(x))
                failed_boolean = True
            else:
                info.append("+{}: {} min, {} second".format(x, minutes, second))
        if failed_boolean:
            user = await self.bot.application_info().owner
            msg = "Background task of cogs have failed!\n"
            msg += "```diff\n{}\n\n{}".format("\n".join(failed), "\n".join(info))
            await self.bot.send_message(user.owner, msg)
        else:
            self.update_info = "\n".join(info)

    async def update_check_loop(self):
        while True:
            counter_loops = 0
            while True:
                if counter_loops == 100:
                    self.counter += 1
                    utils.prPurple("Update Check Loops check! {}".format(self.counter))
                    counter_loops = 0
                await self.update_check()
                await asyncio.sleep(300)

def setup(bot):
    bot.add_cog(Tools(bot))

