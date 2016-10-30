from discord.ext import commands
from datetime import datetime
from .utils import utils
import traceback
import asyncio

class Remind(): #Allow to welcome new members who join server. If it enable, will send them a message.
    def __init__(self,bot):
        self.bot = bot
        self.redis = bot.db.redis
        self.loop = asyncio.get_event_loop()
        self.loop_reminder_timer = self.loop.create_task(self.timer())

    async def timer(self): #Checking if there is remindme task that bot lost during shutdown/restart (losing data from memory)
        utils.prYellow("Remindme Timer start")
        server_list = list(self.bot.servers)
        for server in server_list: #checking each server
            get_time  = datetime.now().timestamp()
            utils.prLightPurple("Checking {}".format(server.name))
            data = await self.redis.hgetall("{}:Remindme:data".format(server.id))
            if data: #if there is exist data then  get info about info about channel
                channel = await self.redis.hgetall("{}:Remindme:channel".format(server.id))
                time = await self.redis.hgetall("{}:Remindme:time".format(server.id))
                for x in data: #run every Id in data and return timer
                    try:
                        remain_time = int(time[x]) - int(get_time)
                        utils.prYellow("Time: {},Channel: {}, Message: {}".format(remain_time,channel[x],data[x]))
                        if remain_time <= 0:
                            await self.bot.send_message(self.bot.get_channel(channel[x]),"I am deeply sorry for not reminded you early!, You was set to remind of this following:\n{}".format(data[x]))
                            await self.redis.hdel("{}:Remindme:data".format(server.id), x)
                            await self.redis.hdel("{}:Remindme:channel".format(server.id), x)
                            await self.redis.hdel("{}:Remindme:time".format(server.id), x)
                        else:
                            self.loop.create_task(self.time_send(channel[x],data[x],remain_time,server.id,x))
                    except:
                        utils.prRed(traceback.format_exc())

    async def time_send(self,channel,msg,time,server,x):
        await asyncio.sleep(time)
        await self.bot.send_message(self.bot.get_channel(channel),msg)
        await self.redis.hdel("{}:Remindme:data".format(server), x)
        await self.redis.hdel("{}:Remindme:channel".format(server), x)
        await self.redis.hdel("{}:Remindme:time".format(server), x)

    @commands.command(hidden=True,pass_context=True)
    async def remindme(self,ctx,get_time,*,message=""):
        time = get_time.split(":")
        remind_time = 0
        msg = "Time set "
        id_time = 0
        print(message)
        if len(time) == 3:
            remind_time += int(time[0])*3600 + int(time[1])*60+ int(time[2])
            msg += "{} hours {} minute {} second".format(time[0],time[1],time[2])
        elif len(time) == 2:
            remind_time += int(time[0])*60 + int(time[1])
            msg += "{} minute {} second".format(time[0],time[1])
        else:
            msg += "{} second".format(time[0])
            remind_time += int(time[0])
        if not message:
            message = "{}, You were reminded for something.".format(ctx.message.author.mention)
        else:
            message = "{}, You were reminded of the following: ```fix\n{}\n```".format(ctx.message.author.mention,message)
        if remind_time >= 60: #if it more than 1 hours, then add id so it can remind you in cases
            time = datetime.now().timestamp() + remind_time
            server = ctx.message.server.id
            id_time =  await self.redis.incr("{}:Remindme:ID".format(server))
            await self.redis.hset("{}:Remindme:data".format(server),id_time,message)
            await self.redis.hset("{}:Remindme:channel".format(server),id_time,ctx.message.channel.id)
            await self.redis.hset("{}:Remindme:time".format(server),id_time,int(time))

        await self.bot.say(msg,delete_after=30)
        await asyncio.sleep(remind_time)
        await self.bot.say(message)
        if remind_time >= 60: #cleaning them up
            server = ctx.message.server.id
            await self.redis.hdel("{}:Remindme:data".format(server),id_time)
            await self.redis.hdel("{}:Remindme:channel".format(server),id_time)
            await self.redis.hdel("{}:Remindme:time".format(server),id_time)


def setup(bot):
    bot.add_cog(Remind(bot))
