from discord.ext import commands
from datetime import datetime
from .utils import utils
import traceback
import asyncio
import pytz
import sys

#TODO
"""
add daily/weekly/monthly remindme
add rerun remindme.



Data structure
atm:
{Server_ID}:Remindme:data
{Server_ID}:Remindme:channel
{Server_ID}:Remindme:time

to maybe

Remindme:once:main
Remindme:once:ID  #id counter, so we can add unqiue id to it.
Remindme:once:{id}

Remindme:repeat:main
Remindme:repeat:ID  #id counter, so we can add unqiue id to it.
Remindme:repeat:{id}

final
Remindme:user:{ID} #for storing ID into it so we can see a list.
"""
class Remind:
    def __init__(self,**kwargs):
        self.member = int(kwargs.get("member")) #member ID (int)
        self.message = kwargs.get("message")#string message that user want to remember
        self.channel = int(kwargs.get("channel")) #channel ID (int)
        self.id_time = kwargs.get("id_time")
        self.current_time = kwargs.get("current") #unix second (int) #to get to.
        self.second = kwargs.get("second") # original second
        self.type = kwargs.get("type")
        self.origin_data = kwargs.get("origin")

    def get_data(self):
        return {"member":self.member,"current":self.current_time,"second":self.second,
                "message":self.message,"channel":self.channel,"id_time":self.id_time,
                "type":self.type,"origin":str(self.origin_data)}

    #update unix time?
    def update_unix(self):
        self.current_time = datetime.now().timestamp() + self.second
        return self.current_time

    def calculate(self):
        """
        Args:
            data: list of string

        Returns:
            total second

        We create sec_multi and have it range from min to month.
        Run a loops backward, since we are starting from right side of data (e.g [hh,mm,ss], then multi from left side)
        """
        sec_multi = [1,60,3600,86400,604800,2628000] #sec,min,hour,day,week,month
        total = 0
        count = 0
        for i in range(len(self.origin_data) - 1,-1,-1): #running loops backward
            total += int(self.origin_data[i]) * sec_multi[count]
            count += 1

        self.second = total
        self.update_unix()
        return total

    def create_remind_msg(self):
        time = self.origin_data
        date = ["second","minute","hour","day","week","month"]
        msg = "Time set "
        count = 0
        for i in range(len(time) - 1,-1,-1): #running loops backward
            msg += "{} {}{}, ".format(time[count],date[i],"s" if int(time[count]) > 1 else "")
            count += 1
        return msg

    def get_remain_sec(self):
        return self.current_time - datetime.now().timestamp()

# class Repeat_Remind(Remind):



class Remindme:
    def __init__(self,bot):
        self.bot = bot
        self.redis = bot.db.redis
        self.loop = asyncio.get_event_loop()
        self.loop_reminder_timer = self.loop.create_task(self.timer())
        self.loop_dict = {}
        self.loop_list = []

    def __unload(self):
        self.loop_reminder_timer.cancel()
        for x in self.loop_list:
            x.cancel()
        utils.prPurple("unload remindme task")


    #old one, use this template.
    async def timer(self): #Checking if there is remindme task that bot lost during shutdown/restart (losing data from memory)
        await asyncio.sleep(5)#give it a moment..
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
                            try:
                                chan = self.bot.get_channel(int(channel[x]))
                                if chan:
                                    await chan.send("I am deeply sorry for not reminding you earlier! You were reminded of the following:\n{}".format(data[x]))
                            except:
                                pass
                            await self.redis.hdel("{}:Remindme:data".format(guild.id), x)
                            await self.redis.hdel("{}:Remindme:channel".format(guild.id), x)
                            await self.redis.hdel("{}:Remindme:time".format(guild.id), x)
                        else:
                            self.loop_list.append(self.loop.create_task(self.time_send(channel[x],data[x],remain_time,guild.id,x)))
                    except:
                        utils.prRed(traceback.format_exc())

    async def time_send(self,channel,msg,time,guild,x):#old one
        await asyncio.sleep(time)
        channel =  self.bot.get_channel(int(channel))
        if channel:
            await channel.send(msg)
        await self.redis.hdel("{}:Remindme:data".format(guild), x)
        await self.redis.hdel("{}:Remindme:channel".format(guild), x)
        await self.redis.hdel("{}:Remindme:time".format(guild), x)

    async def send_message(self,remind):
        """Sending message to channel."""
        utils.prGreen("under send message")
        await asyncio.sleep(remind.get_remain_sec())
        chan = self.bot.get_channel(remind.channel)
        utils.prPurple("wew")
        msg = await chan.send(remind.message)
        if remind.type == "Once":
            utils.prPurple("under once if ")
            rec = utils.Embed_page(self.bot,[])
            # reaction_list += [["\U0001f501", self.planning]]
            await msg.add_reaction("\U0001f501")
            rect, user = await rec.wait_for_react(check = lambda r,u: r.message.id == msg.id and u.id == remind.member
                                           and str(r.emoji) =="\U0001f501", timeout = 30)
            utils.prYellow(rect)
            utils.prYellow(user)
            await msg.clear_reactions()
            if rect is None:
                utils.prPurple("rect is None")
                return await self.redis.srem("Remindme:Once:main",remind.id_time)
        utils.prCyan("boi")
        remind.update_unix()
        return await self.send_message(remind)


    def start_run(self,remind):
        self.loop_dict[remind.id_time] = self.loop.create_task(self.send_message(remind))

    async def save_data(self,remind,member):
        """

        Args:
            type: once or repeat.
            remind: Remind object
            member: Member ID

        Returns:

        """
        key = "Remindme:{}".format(remind.type) #shortcut
        id_time =  await self.redis.incr("{}:ID".format(key))
        remind.id_time = id_time
        await self.redis.sadd("{}:main".format(key),id_time)
        utils.prYellow(remind.get_data())
        await self.redis.hmset_dict("{}:task:{}".format(key,id_time),remind.get_data())
        await self.redis.sadd("{}:user:{}".format(key,member),id_time)

    @commands.command(hidden=True,pass_context=True)
    async def remindme(self,ctx,get_time,*,message=""):
        time = get_time.split(":")
        if not time[0].isdigit(): #checking if it int or not.
            return await ctx.send(content = "You enter the format wrong! It should be look like this {}remindme hh:mm:ss message".format(ctx.prefix),delete_after = 10)
        #make message for user.
        msg = ctx.message
        if not message:
            message = "{}, unspecified reminder.".format(msg.author.mention)
        else:
            message = "{}, Reminder: ```fix\n{}\n```".format(msg.author.mention,message)
        #create Remind object and then run calculate it.
        remind = Remind(member = msg.author.id, message = message, channel = msg.channel.id,origin = time,type = "Once")
        if remind.calculate() > 94610000: #if it greater than 3 year.
            return ctx.send(content = "There no way that I will remind you in at least 3 years time.", delete_after = 10)
        await self.save_data(remind,msg.author.id)
        await ctx.send(content = remind.create_remind_msg(),delete_after = 15)
        self.start_run(remind)

    @commands.command(hidden = True)
    async def timezone(self,ctx,initial):
        """
        Allow to set timezone of your for convenience setting time.
        for example
        !timezone GB
        !timezone US
        If there is multi timezone, it will asked you which one.
        If you have used wrong initial, it will show a list of country with first letter.

        GB is Great Britian
        CA is Canada
        US is USA
        etc.
        """
        country = pytz.country_names.get(initial)#getting country
        if country is None: #if it None then we will need to find it.
            country_list = [x for x in pytz.country_names if initial[0] == x[0]] #Getting a list of country that have first char so user can say which one is their
            temp = ["{}. {}".format(x[0],x[1]) for x in enumerate(country_list,start = 1)]
            answer = await utils.input(self.bot,ctx, "Enter the number for your country:\n{}".format("\n".join(temp)),
                                       lambda msg: msg.content.isdigit() and ctx.message.author == msg.author and int(msg.content) > 0 and int(msg.content) <= len(country_list))
            initial = country_list[int(answer.content) - 1]
        timezone = pytz.country_timezones.get(initial) #getting timezone now
        if len(timezone) != 1: #if timezone are multi then we need to ask user which one.
            temp =["{}. {}".format(x[0],x[1]) for x in enumerate(timezone,start = 1)]
            answer = await utils.input(self.bot,ctx,"Enter the number for timezone:\n{}".format("\n".join(temp)),
                                       lambda msg: msg.content.isdigit() and ctx.message.author == msg.author and int(msg.content) > 0 and int(msg.content) <= len(timezone))
            timezone = timezone[int(answer.content) -1]
        await ctx.send("I have set {}".format(timezone), delete_after = 10)
        await self.redis.hset("Remindme:Profile:{}".format(ctx.message.author.id),"timezone",timezone)


def setup(bot):
    bot.add_cog(Remindme(bot))
