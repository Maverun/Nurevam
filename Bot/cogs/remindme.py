from discord.ext import commands
from datetime import datetime, timedelta
from .utils import utils
import traceback
import asyncio
import pytz

class Remindme(commands.Cog): #Allow to welcome new members who join guild. If it enable, will send them a message.
    def __init__(self,bot):
        self.bot = bot
        self.redis = bot.db.redis
        self.loop = asyncio.get_event_loop()
        self.loop_reminder_timer = self.loop.create_task(self.timer())
        self.loop_list = []

    def cog_unload(self):
        self.loop_reminder_timer.cancel()
        for x in self.loop_list:
            x.cancel()
        utils.prPurple("unload remindme task")

    async def clear(self,gid,tid):
        await self.redis.hdel("{}:Remindme:data".format(gid), tid)
        await self.redis.hdel("{}:Remindme:channel".format(gid), tid)
        await self.redis.hdel("{}:Remindme:time".format(gid), tid)
    
    async def timer(self): #Checking if there is remindme task that bot lost during shutdown/restart (losing data from memory)
        await asyncio.sleep(10)#give it a moment..
        utils.prYellow("Remindme Timer start")
        guild_list = list(self.bot.guilds)
        for guild in guild_list: #checking each guild
            get_time  = datetime.now().timestamp()
            utils.prLightPurple("Checking {}".format(guild.name))
            data = await self.redis.hgetall("{}:Remindme:data".format(guild.id))
            if data: #if there is exist data then  get info about info about channel
                channel = await self.redis.hgetall("{}:Remindme:channel".format(guild.id))
                time = await self.redis.hgetall("{}:Remindme:time".format(guild.id))
                for x in data: #run every Id in data and return timer
                    try:
                        remain_time = int(time[x]) - int(get_time)
                        utils.prYellow("Time: {},Channel: {}, Message: {}".format(remain_time,channel[x],data[x]))
                        if remain_time <= 0:
                            chan = self.bot.get_channel(int(channel[x]))
                            if chan:
                                await chan.send("I am deeply sorry for not reminding you earlier! You were reminded of the following:\n{}".format(data[x]))
                                await self.clear(guild.id,x)
                        else:
                            self.loop_list.append(self.loop.create_task(self.time_send(channel[x],data[x],remain_time,guild.id,x)))
                    except:
                        utils.prRed(traceback.format_exc())

    async def time_send(self,channel,msg,time,guild,x):
        await asyncio.sleep(time)
        channel =  self.bot.get_channel(int(channel))
        if channel:
            await channel.send(msg)
        await self.clear(guild,x)

    @commands.command(hidden =  True)
    async def setTimezoneRemind(self,ctx,timez):
        try:
            #so we are checking if this timezone exists, if no error, we are clear.
            #I will make this command more sense or pretty when I get a chance to rewrite them.... #TODO
            tz = pytz.timezone(timez)
            await self.redis.set("Profile:{}:Remind_Timezone".format(ctx.author.id),timez)
            return await ctx.send("Timezone set for your remind only!",delete_after = 30)
        except pytz.UnknownTimeZoneError:
            await ctx.send("There is no such a timezone, please check a list from there <https://en.wikipedia.org/wiki/List_of_tz_database_time_zones> under **TZ database Name**",delete_after = 30)

    async def split_time(self,t):
        t = t.replace(".",":")
        t = t.split(":")
        if all(x.isdigit() for x in t) is False:
            await self.bot.say(ctx,content = "You enter the format wrong! It should be look like this {}remindtime hh:mm:ss message".format(ctx.prefix))
            return None
        return t

    @commands.command(hidden=True,pass_context=True,aliases=["rt"])
    async def remindtime(self,ctx,get_time,*,message=""):
        #Split them and check if  they are valid.
        time = await self.split_time(get_time)
        if time is None: return
        
        if len(time) == 1:
            time.append('0')
            time.append('0')
        elif len(time) == 2:
            time.append('0')

        if 0 > int(time[0]) or int(time[0]) > 23 or 0 > int(time[1]) or int(time[1]) > 59 or 0 > int(time[2]) or int(time[2]) > 59:
            return await self.bot.say(ctx,content = "You enter the number out of range than they should!")

        #we are grabbing timezone from user set, if user didnt set, it will return None, and when we  create timezone, it will auto select UTC format.
        timezone = await self.redis.get("Profile:{}:Remind_Timezone".format(ctx.author.id))
        timez = pytz.timezone(timezone or "UTC") #if none, then UTC default.

        time_set = datetime.now(timez).replace(hour=int(time[0]),minute=int(time[1]),second=int(time[2]))
        time_now = datetime.now(timez)

        delta_time = time_set - time_now
        if time_set < time_now:
            delta_time += timedelta(days=1)

        await self.remindme_base(ctx,str(timedelta(seconds=int(delta_time.total_seconds()))),message=message)
        
    @commands.command(hidden=True,pass_context=True,aliases=["rm"])
    async def remindme(self,ctx,get_time,*,message=""):
        await self.remindme_base(ctx,get_time,message=message)
        
    async def remindme_base(self,ctx,get_time,*,message=""):
        #Split them and check if  they are valid.
        time = await self.split_time(get_time)
        if time is None: return
        remind_time = 0
        msg = "Time set "
        id_time = 0
        if len(time) == 3:
            remind_time += int(time[0])*3600 + int(time[1])*60 + int(time[2])
            msg += "{} hours {} minute {} second".format(time[0],time[1],time[2])
        elif len(time) == 2:
            remind_time += int(time[0])*60 + int(time[1])
            msg += "{} minute {} second".format(time[0],time[1])
        else:
            remind_time += int(time[0])
            msg += "{} second".format(time[0])
        if not message:
            message = "{}, unspecified reminder.".format(ctx.message.author.mention)
        else:
            message = "{}, Reminder: ```fix\n{}\n```".format(ctx.message.author.mention,message)

        if remind_time >= 60: #if it more than 1 hours, then add id so it can remind you in cases
            time = datetime.now().timestamp() + remind_time
            guild = ctx.message.guild.id
            id_time =  await self.redis.incr("{}:Remindme:ID".format(guild))
            await self.redis.hset("{}:Remindme:data".format(guild),id_time,message)
            await self.redis.hset("{}:Remindme:channel".format(guild),id_time,ctx.message.channel.id)
            await self.redis.hset("{}:Remindme:time".format(guild),id_time,int(time))

        await ctx.send(msg,delete_after=30)
        await asyncio.sleep(remind_time)
        await ctx.send(message)
        if remind_time >= 60: #cleaning them up
            guild = ctx.message.guild.id
            await self.clear(guild,id_time)

def setup(bot):
    bot.add_cog(Remindme(bot))
