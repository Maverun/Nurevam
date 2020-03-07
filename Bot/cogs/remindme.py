from discord.ext import commands
from datetime import datetime, timedelta
from .utils import utils
import traceback
import asyncio

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
                            await self.redis.hdel("{}:Remindme:data".format(guild.id), x)
                            await self.redis.hdel("{}:Remindme:channel".format(guild.id), x)
                            await self.redis.hdel("{}:Remindme:time".format(guild.id), x)
                        else:
                            self.loop_list.append(self.loop.create_task(self.time_send(channel[x],data[x],remain_time,guild.id,x)))
                    except:
                        utils.prRed(traceback.format_exc())

    async def time_send(self,channel,msg,time,guild,x):
        await asyncio.sleep(time)
        channel =  self.bot.get_channel(int(channel))
        if channel:
            await channel.send(msg)
        await self.redis.hdel("{}:Remindme:data".format(guild), x)
        await self.redis.hdel("{}:Remindme:channel".format(guild), x)
        await self.redis.hdel("{}:Remindme:time".format(guild), x)

    @commands.command(hidden=True,pass_context=True)
    async def remindtime(self,ctx,get_time,*,message=""):     
        time = get_time.split(":")
        if not time[0].isdigit():
            return await self.bot.say(ctx,content = "You enter the format wrong! It should be look like this {}remindtime hh:mm:ss message".format(ctx.prefix))
        if len(time) == 1:
            time.append('0')
            time.append('0')
        elif len(time) == 2:
            time.append('0')
        
        time_set = datetime.utcnow().replace(hour=int(time[0]),minute=int(time[1]),second=int(time[2]))
        time_now = datetime.utcnow()
        delta_time = time_set - time_now
        if time_set < time_now:
            delta_time += timedelta(days=1)
            
        await self.remindme_base(ctx,str(timedelta(seconds=int(delta_time.total_seconds()))),message=message)
        
    @commands.command(hidden=True,pass_context=True)
    async def remindme(self,ctx,get_time,*,message=""):
        await self.remindme_base(ctx,get_time,message=message)
        
    async def remindme_base(self,ctx,get_time,*,message=""):
        time = get_time.split(":")
        if not time[0].isdigit():
            return await self.bot.say(ctx,content = "You enter the format wrong! It should be look like this {}remindme hh:mm:ss message".format(ctx.prefix))
        remind_time = 0
        msg = "Time set "
        id_time = 0
        print(message)
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
            await self.redis.hdel("{}:Remindme:data".format(guild),id_time)
            await self.redis.hdel("{}:Remindme:channel".format(guild),id_time)
            await self.redis.hdel("{}:Remindme:time".format(guild),id_time)


def setup(bot):
    bot.add_cog(Remindme(bot))
