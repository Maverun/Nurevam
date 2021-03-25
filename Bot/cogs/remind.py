from datetime import datetime, timedelta
from discord.ext import commands
from .utils import utils
import traceback
import asyncio
import discord
import pytz

loop_list = {}

class Remind(commands.Cog): #This is to remind user about task they set.
    def __init__(self,bot):
        self.bot = bot
        self.redis = bot.db.redis
        self.loop = asyncio.get_event_loop()
        self.loop_reminder_timer = self.loop.create_task(self.timer())

    def cog_unload(self):
        self.loop_reminder_timer.cancel()
        for val in loop_list.values():
            val.cancel()
        utils.prPurple("unload remindme task")

    async def clear(self,gid,uid,mid):
        lp = loop_list.pop(mid,None) #pop out of list. Cast int just in case
        if lp is not None:
            lp.cancel() #just in case it was running and someone CANCEL IT

        await self.redis.lrem(f"{gid}:Remindme:Person:{uid}",1,mid)
        await self.redis.hdel(f"{gid}:Remindme:member",mid)
        await self.redis.hdel(f"{gid}:Remindme:data", mid)
        await self.redis.hdel(f"{gid}:Remindme:channel", mid)
        await self.redis.hdel(f"{gid}:Remindme:time", mid)

    async def timer(self): #Checking if there is remindme task that bot lost during shutdown/restart (losing data from memory)
        await asyncio.sleep(5)#give it a moment..
        utils.prYellow("Remindme Timer start")
        guild_list = list(self.bot.guilds)
        for guild in guild_list: #checking each guild
            get_time  = datetime.now().timestamp()
            utils.prLightPurple(f"Checking {guild.name}")
            data = await self.redis.hgetall(f"{guild.id}:Remindme:data")
            if data: #if there is exist data then  get info about info about channel
                author_list = await self.redis.hgetall(f"{guild.id}:Remindme:member")
                channel = await self.redis.hgetall(f"{guild.id}:Remindme:channel")
                time = await self.redis.hgetall(f"{guild.id}:Remindme:time")
                for mid in data: #run every Id in data and return timer
                    try:
                        if author_list.get(mid): #to be compaitable with old legacy.
                            check_str = f"{guild.id}:Remindme:Person:{author_list.get(mid)}"
                            if mid not in await self.redis.lrange(check_str,0,-1):
                                utils.prRed("RM:No longer in Person, so delete....")
                                await self.clear(guild.id,author_list.get(mid),mid)
                                continue #Somehow if it cant delete old one we might do it here.
                            chan = guild.get_channel(int(channel[mid]))
                            author = guild.get_member(int(author_list[mid]))
                        #Once Legacy will be gone, there might be some leftover
                        #such as one that was set really long.. that last years...
                        #those will be likely to be delete.
                        remain_time = int(time[mid]) - int(get_time)
                        utils.prYellow(f"Time: {remain_time},Channel: {channel[mid]}, Message: {data[mid]}")
                        if remain_time <= 0:
                            if chan:
                                await chan.send(f"{author.mention}\nI am deeply"
                                                " sorry for not reminding you earlier!"
                                                " You were reminded of the following:\n"
                                                f"```fix\n {data[mid]} \n```")
                                await self.clear(guild.id,author.id,mid)
                        else:
                            if author_list.get(mid):
                                task = self.loop.create_task(self.time_send(
                                                    chan,author,data[mid],
                                                   remain_time,guild.id,mid))
                            else: #Old legacy... Soon to be delete once confirm 
                                task = self.loop.create_task(self.old_time_send(
                                                    channel[mid],data[mid],
                                                    remain_time,guild.id,mid))
                            loop_list[mid] = task
                    except:
                        utils.prRed(traceback.format_exc())

    async def time_send(self,channel,author,msg,time,guild,mid):
        await asyncio.sleep(time)
        #if it not in list, then dont send it as it is likely cancel.
        if channel and loop_list.get(mid): #Making sure it not in list...
            await self.send_msg(channel,author,msg)
        await self.clear(guild,author.id,mid)

    async def old_time_send(self,channel,msg,time,guild,x): #Legacy. Will delete
        await asyncio.sleep(time)
        channel =  self.bot.get_channel(int(channel))
        if channel:
            await channel.send(msg)
        await self.redis.hdel("{}:Remindme:data".format(guild), x)
        await self.redis.hdel("{}:Remindme:channel".format(guild), x)
        await self.redis.hdel("{}:Remindme:time".format(guild), x)

    async def send_msg(self,ctx,author,msg):
        await ctx.send(f"{author.mention} Reminder:\n```fix\n{msg}\n```")

    @commands.command(hidden =  True)
    async def setTimezoneRemind(self,ctx,timez):
        try:
            #so we are checking if this timezone exists,
            #if no error, we are clear.
            #I will make this command more sense or pretty 
            #when I get a chance to rewrite them.... #TODO
            tz = pytz.timezone(timez)
            await self.redis.set("Profile:{}:Remind_Timezone".format(ctx.author.id),tz)
            return await ctx.send("Timezone set for your remind only!",delete_after = 30)
        except pytz.UnknownTimeZoneError:
            await ctx.send("There is no such a timezone, please check a list from there <https://en.wikipedia.org/wiki/List_of_tz_database_time_zones> under **TZ database Name**",delete_after = 30)

    async def split_time(self,ctx,t):
        t = t.replace(".",":")
        t = t.split(":")
        if all(x.isdigit() for x in t) is False:
            await self.bot.say(ctx,content = "You enter the format wrong! It should be look like this {}remindtime hh:mm:ss message".format(ctx.prefix))
            return None
        return [int(x) for x in t] #Returning them but first make sure its int!

    @commands.command(hidden=True,pass_context=True,aliases=["rt"])
    async def remindtime(self,ctx,get_time,*,message=""):
        #Split them and check if  they are valid.
        time = await self.split_time(ctx, get_time)
        if time is None: return

        if len(time) == 1:
            time.append(0)
            time.append(0)
        elif len(time) == 2:
            time.append(0)

        if 0 > time[0] or time[0] > 23 or 0 > time[1] or time[1] > 59 or 0 > time[2] or time[2] > 59:
            return await self.bot.say(ctx,content = "You enter the number out of range than they should!")

        #we are grabbing timezone from user set, if user didnt set,
        #it will return None, and when we  create timezone,
        #it will auto select UTC format.
        tz = await self.redis.get(f"Profile:{ctx.author.id}:Remind_Timezone")
        timez = pytz.timezone(tz or "UTC") #if none, then UTC default.

        time_set = datetime.now(timez).replace(hour   = time[0],
                                               minute = time[1],
                                               second = time[2])
        time_now = datetime.now(timez)

        delta_time = time_set - time_now
        if time_set < time_now:
            delta_time += timedelta(days=1)
        utils.prGreen(ctx)
        await self.remindme_base(ctx,
                                 str(timedelta(seconds=int(delta_time.total_seconds())))
                                 ,message=message)

    @commands.command(hidden=True,pass_context=True,aliases=["rm"])
    async def remindme(self,ctx,get_time,*,message=""):
        await self.remindme_base(ctx,get_time,message=message)

    async def remindme_base(self,ctx,get_time,*,message=""):
        #Split them and check if  they are valid.
        time = await self.split_time(ctx,get_time)
        if time is None: return
        remind_time = 0
        msg = "Time set "
        if len(time) == 3:
            remind_time += time[0]*3600 + time[1]*60 + time[2]
            msg += "{} hours {} minute {} second".format(time[0],time[1],time[2])
        elif len(time) == 2:
            remind_time += time[0]*60 + time[1]
            msg += "{} minute {} second".format(time[0],time[1])
        else:
            remind_time += time[0]
            msg += "{} second".format(time[0])
        if not message: message = "unspecified reminder"
        rid = None
        if remind_time >= 60:
            #if it more than 1 min, then add id so it can remind you in cases
            #bot goes down...
            time = datetime.now().timestamp() + remind_time
            #making ID of Message, User/Member, Guild
            print(ctx)
            mid = ctx.message.id
            uid = ctx.author.id
            gid = ctx.guild.id
            cid = ctx.channel.id
            #we will be using idea as LINK-LIST where we will push msg ID to tail
            #This allow to keep as in order for ID so we can cancel when need
            rid = await self.redis.rpush(f"{gid}:Remindme:Person:{uid}",mid)
            #Setting MSGID to UserID, so we can find who responsiblity for this
            await self.redis.hset(f"{gid}:Remindme:member",mid,uid)
            await self.redis.hset(f"{gid}:Remindme:data",mid,message)
            await self.redis.hset(f"{gid}:Remindme:channel",mid,cid)
            await self.redis.hset(f"{gid}:Remindme:time",mid,int(time))

        msg = f"{msg}\nID: {rid}" if rid else msg
        await ctx.send(msg,delete_after=30)

        task = self.loop.create_task( self.time_send(ctx.channel, ctx.author,
                                                    message, remind_time,
                                                    ctx.guild.id, str(ctx.message.id)))
        loop_list[str(ctx.message.id)] = task

    @commands.command(aliases = ["rl"], hidden = True)
    async def remindlist(self, ctx ):
        #There we will show a list of user's ID reminder.
        uid = ctx.author.id
        gid = ctx.guild.id

        current_time = datetime.now().timestamp()
        id_list   = await self.redis.lrange(f"{gid}:Remindme:Person:{uid}",0,-1)
        data_list = await self.redis.hgetall(f"{gid}:Remindme:data")
        time_list = await self.redis.hgetall(f"{gid}:Remindme:time")
        if not any(id_list): return await ctx.send("You haven't set any reminder!")
        id_col = time_col = msg_col = ""
        for i, rid in enumerate(id_list,start = 1):
            old_time = time_list.get(rid,None)
            if old_time is None: continue #TODO TEMP FIX
            remain_time = int(old_time) - current_time
            hold = [-1,-1,-1]
            if remain_time >= 3600:
                hold[0] = remain_time/3600 #hours
                remain_time %= 3600 #get remiander min
            if remain_time >= 60: #if min leftover
                hold[1] = remain_time/60 #min
                remain_time %= 60 #get remainder second
            hold[2] = remain_time
            ft = ["h","m","s"]
            #we will then convert them to time message (5H,2M) etc.
            #Cast int to cut off decimal
            rtmsg = " ".join(f"{int(hold[i])}{ft[i]}" for i in range(3) if hold[i] != -1 )
            #now we will set message, with 30 char of "data" to remind user
            msg = data_list[rid]
            id_col += f"{i}\n"
            time_col += f"{rtmsg}\n"
            msg_col += f"{msg[:30]}"
            msg_col += "...\n" if len(msg) > 30 else "\n"
        #set up embeds and add each to each field then send
        e = discord.Embed()
        e.add_field(name = "ID",value = id_col)
        e.add_field(name = "Time Remain",value = time_col)
        e.add_field(name = "Message",value = msg_col)
        await ctx.send(embed = e)

    @commands.command(aliases = ["rc"], hidden = True)
    async def remindcancel(self, ctx, raw_rid:commands.Greedy[int],
                           is_all:str=""):
        #We will just assume user know what they are doing lol
        gid = ctx.guild.id
        uid = ctx.author.id
        if is_all == "all":
            raw_len = await self.redis.llen(f"{gid}:Remindme:Person:{uid}")
            raw_rid = [x for x in range(raw_len)]
        if len(raw_rid) == 0:
            return await ctx.send("You need to enter IDs (or \"all\")!")
        raw_rid = sorted(raw_rid, reverse = True) #Sorting and in reverse
        #Just in case user enter 1 3 then realized need to include 2.
        for ri in raw_rid:
            #First we will get what element it is at. Index start at 0 duh.
            rid = await self.redis.lindex(f"{gid}:Remindme:Person:{uid}",ri-1)
            #if we get none, out of range!
            if rid is None:
                return await ctx.send("Out of range!", delete_after = 30)
            #Since we are here, then that mean it is inside, and we will just pop it
            await self.clear(gid,uid,rid) #Clear up from DB
        await ctx.send("Done.\nNote: Any ID after you enter will go down by 1")




def setup(bot):
    bot.add_cog(Remind(bot))
