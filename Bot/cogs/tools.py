from discord.ext import commands
from .utils import utils
import traceback
import datetime
import discord
import asyncio
import inspect
import logging
import psutil
import glob
import git

log = logging.getLogger("Nurevam")


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
        self.bot.say_edit = bot.say
        self.update_info = None
        self.back_up_info = None
        self.counter = 0
        asyncio.get_event_loop().create_task(self.clean_command())
        asyncio.get_event_loop().create_task(self.timer_update())
        asyncio.get_event_loop().create_task(self.update_check_loop())

    async def on_command_completion(self,ctx):
        await self.redis.hincrby("command_count",ctx.command.name)
        await self.redis.hincrby("temp_command_count",ctx.command.name)

    async def clean_command(self):
        return await self.redis.delete("temp_command_count")

    #Load/Unload/Reload cogs
    @commands.command(hidden=True)
    @commands.check(utils.is_owner)
    async def load(self,ctx,*, module : str):
        """Loads a module
        Example: load cogs.mod"""
        module ="cogs."+module.strip()
        if not module in list_cogs():
            await ctx.send("{} doesn't exist.".format(module))
            return
        try:
            self.bot.load_extension(module)
        except Exception as e:
            await ctx.send('{}: {}'.format(type(e).__name__, e))
            raise
        else:
            await ctx.send("Enabled.".format(module))

    @commands.command(hidden=True)
    @commands.check(utils.is_owner)
    async def unload(self,ctx,*, module : str):
        """Unloads a module
        Example: unload cogs.mod"""
        module ="cogs."+module.strip()
        if not module in list_cogs():
            await ctx.send("That module doesn't exist.")
            return
        try:
            self.bot.unload_extension(module)
        except Exception as e:
            await ctx.send('{}: {}'.format(type(e).__name__, e))
        else:
            await ctx.send("Module disabled.")

    @commands.command(name="reload",hidden=True)
    @commands.check(utils.is_owner)
    async def _reload(self,ctx,*, module : str):
        """Reloads a module
        Example: reload cogs.mod"""
        module ="cogs."+module.strip()
        if not module in list_cogs():
            await ctx.send("This module doesn't exist.".format(module))
            return
        try:
            self.bot.unload_extension(module)
            self.bot.load_extension(module)
        except Exception as e:
            await ctx.send('\U0001f52b')
            await ctx.send('{}: {}'.format(type(e).__name__, e))
            raise
        else:
            await ctx.send("Module reloaded.")

    @commands.command(name="reload-all",hidden=True)
    @commands.check(utils.is_owner)
    async def reload_all(self,ctx):
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
        await ctx.send("```fix\n{}\nhas been reload\n```".format("\n".join(cogs)))

    @commands.command(hidden=True)
    @commands.check(utils.is_owner)
    async def debug(self, ctx, *, code : str):
        print("OK")
        """Evaluates code."""
        code = code.strip('` ')
        python = '```py\n{}\n```'
        result = None

        env = {
            'bot': self.bot,
            'ctx': ctx,
            'message': ctx.message,
            'guild': ctx.message.guild,
            'channel': ctx.message.channel,
            'author': ctx.message.author,
            'redis': utils.redis
        }

        env.update(globals())

        try:
            result = eval(code, env)
            if inspect.isawaitable(result):
                result = await result
        except Exception as e:
            await ctx.send(python.format(type(e).__name__ + ': ' + str(e)))
            return

        if len(python.format(result)) >= 2000:
            msg = await utils.send_hastebin(python.format(result))
        else:
            msg = python.format(result)

        await ctx.send(msg)

    @commands.group(invoke_without_command=True)
    @commands.check(utils.is_owner)
    async def owner(self,ctx):
        pass

    @owner.command()
    @commands.check(utils.is_owner)
    async def enable(self,ctx,*,Cogs):
        check = await self.redis.hget("{}:Config:cogs".format(ctx.message.guild.id),Cogs)
        print(check)
        if check == "off":
            await self.redis.hset("{}:Config:cogs".format(ctx.message.guild.id),Cogs,"on")
            await ctx.send("Update.")
        elif check == "on":
            await ctx.send("It is already enable.")

    @owner.command()
    @commands.check(utils.is_owner)
    async def disable(self,ctx,*,Cogs):
        print(Cogs)
        check = await self.redis.hget("{}:Config:cogs".format(ctx.message.guild.id),Cogs)
        if check == "on":
            await self.redis.hset("{}:Config:cogs".format(ctx.message.guild.id),Cogs,"off")
            await ctx.send("Update.")
        elif check == "off":
            await ctx.send("It is already disable.")

    @owner.command()
    @commands.check(utils.is_owner)
    async def logout(self):
        """
        Safetly to logout and close redis nicely.
        """
        await self.bot.logout()
        await self.redis.quit()

    @owner.command(name="list-guild")
    @commands.check(utils.is_owner)
    async def list_guild(self,ctx):
        info = [r.name for r in self.bot.guilds]
        char_name = [str(r.owner) for r in self.bot.guilds]
        for guild in self.bot.guilds:
            name = str(guild)
            guild_id = str(guild.id)
            owner = str(guild.owner)
            total =  guild.member_count
            print("Server: {0:<{first}}[{1}]\tOwner: {2:<{second}}\t Member Count: {3}".format(name,guild_id,owner,total,
                                                                                               first=len(max(info,key=len)),
                                                                                               second = len(max(char_name,key=len))))

    @owner.command()
    @commands.check(utils.is_owner)
    async def upgrade(self,ctx):
        """
        Allow to update, so i can just simple do reload afterward.
        """
        repo = git.cmd.Git("../")
        result = repo.pull()
        await ctx.send("```\n{}\n```".format(result))

    @owner.command()
    @commands.check(utils.is_owner)
    async def update(self,ctx):
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

    @owner.group(invoke_without_command = True)
    @commands.check(utils.is_owner)
    async def site(self,ctx):
        pass

    @site.command()
    @commands.check(utils.is_owner)
    async def add(self,ctx,cog):
        await self.redis.sadd("Website:Cogs",cog.lower())
        return await self.bot.say(ctx,content = u"\U0001F44C")

    @site.command()
    @commands.check(utils.is_owner)
    async def remove(self,ctx,cog):
        await self.redis.srem("Website:Cogs", cog.lower())
        return await self.bot.say(ctx,content = u"\U0001F44C")


    def get_bot_uptime(self): #to calculates how long it been up
        now = datetime.datetime.utcnow()
        delta = now - self.bot.uptime
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        days, hours = divmod(hours, 24)
        if days:
            fmt = '{d}d{h}h{m}m{s}s'
        else:
            fmt = '{h}h{m}m{s}s'

        return fmt.format(d=days, h=hours, m=minutes, s=seconds)


    @owner.group()
    @commands.check(utils.is_owner)
    async def stats(self,ctx):
        """
        Borrowing Danny's idea on this, It will be useful for me to see what up
        """
        process = psutil.Process()
        ram = process.memory_full_info().uss / 1024**2
        cpu = process.cpu_percent() / psutil.cpu_count()
        total_use = await self.redis.hgetall("command_count")
        total_temp_use = await self.redis.hgetall("temp_command_count")
        num_total_use = sum(int(x) for x in total_use.values())
        num_temp_total_use = sum(int(x) for x in total_temp_use.values())
        time = self.get_bot_uptime()
        redis_last_save = datetime.datetime.fromtimestamp(await self.redis.lastsave()).strftime("%Y-%m-%d %H:%M:%S")
        redis_info = await self.redis.info()
        redis_info_msg = "**Uptime Day**:{0[server][uptime_in_days]}\n" \
                         "**Uptime Second**:{0[server][uptime_in_seconds]}\n" \
                         "**Total Key**:{0[keyspace][db0][keys]}\n" \
                         "**Expire Key**:{0[keyspace][db0][expires]}\n" \
                         "**RAM**:{0[memory][used_memory_human]}\n" \
                         "**CPU**:{0[cpu][used_cpu_sys]}\n".format(redis_info)

        embed = discord.Embed()

        embed.add_field(name = "Uptime",value=time)
        embed.add_field(name = "Server",value = str(len(self.bot.guilds)))
        embed.add_field(name = "Member", value = "{} unique\n{} non-unique".format(len(self.bot.users),len(list(self.bot.get_all_members()))))
        embed.add_field(name = "RAM/CPU", value = "{} MiB\n{}%".format(ram,cpu))
        embed.add_field(name = "Command use", value= "**Total**: {}\n**Current**: {}".format(num_total_use,num_temp_total_use))
        embed.add_field(name = "Redis last save",value=redis_last_save)
        embed.add_field(name = "Redis Info",value = redis_info_msg)
        await ctx.send(embed = embed)

    async def update_all(self):
        """
        Updating Thing for website, level every x hours instead of spamming.
        For example, update user's name and their icon for website purpose
        Same for guild icon,name
        """
        # getting data of members, set it so there is no dupe, then put them into data
        info = self.bot.users
        await self.redis.hmset_dict("Info:Icon", dict([(x.id, x.avatar) for x in info if x.avatar]))
        await self.redis.hmset_dict("Info:Name", dict([[x.id, str(x)] for x in info]))

        guild = self.bot.guilds  # same thing with ^^ but guild

        await self.redis.hmset_dict("Info:Server_Icon", dict([[x.id, x.icon] for x in guild if x.icon]))
        await self.redis.hmset_dict("Info:Server", dict([[x.id, x.name] for x in guild]))

        current_Time = datetime.datetime.utcnow().strftime("%b/%d/%Y %H:%M:%S UTC")

        utils.prCyan("{}: Update {} of icon,name!".format(current_Time, len(info)))
        utils.prCyan("{}: Update {} of guild!".format(current_Time, len(guild)))

        if self.update_info:
            utils.prCyan(self.update_info)
        await self.update_check()
        return len(info)

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
                if x in self.bot.cogs:
                    failed.append("-{}: {} min, {} second".format(x, minutes, second))
                    self.bot.unload_extension("cogs.{}".format(x))
                    await asyncio.sleep(2)
                    self.bot.load_extension("cogs.{}".format(x))
                    failed_boolean = True
            else:
                info.append("+{}: {} min, {} second".format(x, minutes, second))
        if failed_boolean:
            msg = "Background task of cogs have failed!\n"
            msg += "```diff\n{}\n\n{}\n```".format("\n".join(failed), "\n".join(info))
            await self.bot.owner.send(msg)
        else:
            self.update_info = "\n".join(info)


    async def update_check_loop(self):
        utils.prPurple("Starting update_check_loop")
        while True:
            counter_loops = 0
            while True:
                if counter_loops == 100:
                    self.counter += 1
                    utils.prPurple("Update Check Loops check! {}".format(self.counter))
                    counter_loops = 0
                await self.update_check()
                await asyncio.sleep(300)

    async def timer_update(self):
        while True:
            await self.update_all()
            await asyncio.sleep(3600)
def setup(bot):
    bot.add_cog(Tools(bot))

