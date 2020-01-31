from prettytable import PrettyTable
from discord.ext import commands
from .utils import utils
import lxml.html
import traceback
import datetime
import asyncio
import aiohttp
import discord
import logging
import html

log = logging.getLogger(__name__)

def html_unscape(term):
    return html.unescape(term)

def html_tag(term):
    return lxml.html.fromstring(term).text_content() #good grief righto?

class Discourse(commands.Cog): #Discourse, a forums types.
    def __init__(self,bot):
        self.bot = bot
        self.redis = bot.db.redis
        self.counter = 0
        self.log_error = {}
        self.bg_dis = utils.Background("discourse",60,30,self.timer,log)
        self.bg_dis_id = utils.Background("discourse_ID",3600,1800,self.timer_update_ID,log)
        self.bg_dis_trust = utils.Background("discourse_ID",10800,7200,self.timer_trust_role,log) #assign role every 2 hours.
        self.bot.background.update({"discourse":self.bg_dis,"discourse_ID":self.bg_dis_id,"discourse_trust_role":self.bg_dis_trust})
        self.bg_dis.start()
        self.bg_dis_id.start()
        self.bg_dis_trust.start()

    def cog_unload(self):
        self.bg_dis.stop()
        self.bg_dis_id.stop()
        self.bg_dis_trust.stop()
        utils.prLightPurple("Unloading Discourse")

    def cog_check(self,ctx):
        return utils.is_enable(ctx,"discourse")

    def logging_info(self,status,link,thread_id,guild_id):
        if isinstance(status,int):
            if status == 404:
                status = "Not found."
            elif status == 410:
                status = "Missing."
            elif status == 403:
                status = "Cannot access it."
            else:
                status = "???:{}".format(status)
        elif bool(status) is True:
            status = "Working."
        elif bool(status) is False:
            status = "Cannot connect."
        else:
            status = "???"
        self.log_error[guild_id] = {"status":status,"link":link,"id":thread_id,"time":datetime.datetime.now()}

    async def repeat_error(self,guild,domain):
        await self.redis.set("{}:Discourse:Temp_off".format(guild), domain, expire=1800)
        count = await self.redis.incr("{}:Discourse:Counting".format(guild))
        await self.redis.expire("{}:Discourse:Counting".format(guild), 3600)
        if count == 10:  # 5 hours later and it is still down, it will auto turn off setting, sorry folks
            utils.prRed("Discourse: Turning off for {}".format(guild))
            await self.redis.hdel('{}:Config:Cogs'.format(guild), "discourse")
            await guild.owner.send("Hello there, it look like your discourse site is down for at least 5 hours?"
                                   " I have disable Discourse plugin on dashboard,"
                                   " so once you got site working again, please enable it again. Sorry for trouble.")

    async def get_update_id(self,guild_id,api_key = "api_key",api_username = "api_username"): #api_key.. sometime it doens't work on certain site, so api work instead, prob due to update or? Will have to look into it later
        if await self.redis.hget('{}:Config:Cogs'.format(guild_id),"discourse") is None:
            return
        if await self.redis.get("{}:Discourse:Temp_off".format(guild_id)):
            log.debug("Site is temp ignore for while, GUILD ID: {}".format(guild_id))
            return
        config = await self.redis.hgetall("{}:Discourse:Config".format(guild_id))
        if not (config):
            return
        try:
            flag,data = await self.get_data(config,"latest",guild_id)
            if flag == True:
                number =[]
                for x in data["topic_list"]["topics"]:
                    number.append(x["id"])
                lastest_id = max(number)
                current_id = int(await self.redis.get("{}:Discourse:ID".format(guild_id)))
                if current_id < lastest_id: #if it not really up to dated.
                    utils.prPurple("This guild [ {} ] for discourse is behind! Current ID: {} and lastest ID:{}".format(guild_id,current_id,lastest_id))
                    await self.redis.set("{}:Discourse:ID".format(guild_id),lastest_id-1) #one behind.
                elif current_id == lastest_id:
                    utils.prPurple("This guild [ {} ] for discourse is same! Current ID: {}".format(guild_id,current_id))
                else:
                    utils.prPurple("This guild [ {} ] for discourse,something not right? Current ID: {} Lastest ID {}".format(guild_id,current_id,lastest_id))
                    #await self.redis.set("{}:Discourse:ID".format(guild_id),lastest_id) #since it is ahead, we should fix it.
        except:
            utils.prRed(traceback.format_exc())
            await self.repeat_error(guild_id,config["domain"])

    async def get_data(self,config,path,guild=None,api_key = "api_key",api_username = "api_username"):
        #Using headers so it can support both http/1 and http/2
        #Two replace, one with https and one with http...
        # utils.prCyan("Under get_data, {}".format(link))
        try:
            if await self.redis.get("{}:Discourse:Temp_off".format(guild)):
                log.debug("Site is temp ignore for while, GUILD ID: {}".format(guild))
                return False,None #None might be best for this?
            headers = {"Host": config["domain"].replace("http://","").replace("https://",""),
                       api_key:config["api_key"],
                       api_username:config["username"]}
            url = "{}/{}.json".format(config["domain"],path)
            async with aiohttp.ClientSession(read_timeout = 15) as discourse:
                async with discourse.get(url,headers=headers) as resp:
                    log.debug(resp.status)
                    if resp.status == 200:
                        return True,await resp.json()
                    elif api_key == "api_key":
                        return await self.get_data(config,path,guild,"Api-Key","Api-Username") #just in case api_key doesn't work. Eventually, once most forums is update to latest, then will start using Api-Key as main now.
                    else:
                        return False,resp.status
        except asyncio.CancelledError: #Just in case here for some reason
            utils.prRed("Under get_data function")
            utils.prRed("Asyncio Cancelled Error")
            return False,None
        except:
            utils.prRed("Under get_data function, server: {}".format(guild))
            utils.prRed(traceback.format_exc())
            await self.repeat_error(guild,config["domain"])
            return False,None #None might be best for this? I hope...-

    async def new_post(self,guild_id):
        log.debug(guild_id)
        if await self.redis.hget('{}:Config:Cogs'.format(guild_id),"discourse") is None:
            return log.debug("Disable")

        config = await self.redis.hgetall("{}:Discourse:Config".format(guild_id))
        log.debug(config) #checking to see if there is config in
        if not (config):
            return
        id_post = await self.redis.get("{}:Discourse:ID".format(guild_id))
        log.debug(id_post)
        if not(id_post):
            return log.debug("ID post is missing")

        data = {}
        status,link,get_post = "???"
        error_count = 0
        while True:
            counter = await self.redis.incr("{}:Discourse:ID".format(guild_id))
            log.debug("Counter is {} - id {}:".format(counter,guild_id))
            self.logging_info(get_post, link, counter, guild_id)
            counter += 1
            link = "{}/t/{}".format(config['domain'],counter)
            status,get_post = await self.get_data(config,"t/{}".format(counter),guild_id)
            if status is False:
                if get_post in (403,410): #private or delete, continue. Altho, for private...it is actually return 404 why....
                    error_count += 1
                    if error_count == 10:
                        break
                    continue
                await self.redis.decr("{}:Discourse:ID".format(guild_id))
                break # it reached not found page. or any other error
            elif status is True:
                log.debug("It have post")
                if get_post["archetype"] == "regular":
                    check_exist = data.get(get_post["category_id"])
                    if check_exist is None:
                        data[get_post["category_id"]] = []
                    #custom msg
                    msg_template = config.get("msg","{title}\t\tAuthor: {author}\n{link}").format(author = get_post["details"]["created_by"]["username"],
                                                                                                  link = link,title =html_unscape(get_post["fancy_title"]),
                                                                                                  summary = html_tag(html_unscape(get_post["post_stream"]["posts"][0]["cooked"])))
                    msg_template = msg_template.replace("\\t","\t").replace("\\n","\n") #a bad fix...
                    if len(msg_template) > 1000:
                        msg_template = msg_template[:1000] + "..." #just in case someone use summary.
                    data[get_post["category_id"]].append(msg_template)
        if data:
            log.debug("Got a data to post to channel")
            raw_channel = await self.redis.hgetall("{}:Discourse:Category".format(guild_id))
            for key,values in data.items():
                log.debug("{} and {}".format(key,values))
                channel = raw_channel.get(str(key),config["channel"])
                if channel == "0":
                    channel = config["channel"]
                elif channel == "-1": #None
                    continue
                #Sending message here
                channel_send = self.bot.get_channel(int(channel))
                if channel_send is None:
                    log.debug("Channel is not found, {}".format(channel))
                    continue
                if len("\n".join(values)) > 2000:
                    for msg in values:
                        await channel_send.send(msg)
                else:
                    await channel_send.send("\n".join(values))
                utils.prLightPurple("\n".join(values))
        log.debug("Finish checking {}".format(guild_id))

    async def check_trust_role(self,guild,level,data,current_list,all_role_trust_level):
        data = data["members"] #getting list of trust level x member
        trust_role_list = {x["id"] for x in data}
        current_list_id = set(current_list).intersection(trust_role_list)
        for discourse_id in current_list_id:
            member = guild.get_member(current_list[discourse_id])
            if guild.me.top_role > member.top_role: #just to make sure i can grant them a role other wise... ignore it
                member_role = {x.id for x in member.roles if x != guild.default_role} #getting id of member's role each
                missing_role = all_role_trust_level - member_role#in case they already have it or not.
                if missing_role:
                    role = [x for x in guild.roles if x.id in missing_role]
                    await member.add_roles(*role,reason = "This member has reached trust level {} on discourse".format(level))

    async def update_role(self,guild):
        if await self.redis.hget('{}:Config:Cogs'.format(guild.id),"discourse") is None:
            return
        elif await self.redis.get("{}:Discourse:trust_bool".format(guild.id)) in ["0",None]: #either owner set it off or None.
            return
        try:
            config = await self.redis.hgetall("{}:Discourse:Config".format(guild.id))
            if not (config): return

            #getting list of user that already link up with discourse. KEY:VALUE = Discourse_ID:Discord_ID
            current_list_user = await self.redis.hgetall("{}:Discourse:Trust_User_ID".format(guild.id))
            current_list_user = [{int(key):int(value)} for key,value in current_list_user.items()]
            if bool(current_list_user) is False: return #if plugin is on and already set roles, but no one havent link.. well..
            current_list_user = current_list_user[0]

            all_role_list = set() #creating set {} so we can union them.
            for x in range(1,5):
                #this here will add trust_level_role to previous, this reason is that when doing api call, they dont include 0 but only one that member is at.
                #so if member is at level 2, then 0 and 1 will also include, etc.
                current_role_trust_level = await self.redis.smembers("{}:Discourse:trust_role{}".format(guild.id, x))
                if current_role_trust_level.count('') >= 1:  current_role_trust_level.remove('') #if it empty string '' then remove it.
                all_role_list = all_role_list.union({int(x) for x in current_role_trust_level}) #making sure all role id are in int.
                flag,data = await self.get_data(config,"groups/trust_level_{}/members",guild) #getting trust level x row list.
                if flag == 200 and bool(all_role_list): #if role is empty, well obviously cant give one to user.
                    await self.check_trust_role(guild,x,data,current_list_user,all_role_list)
        except:
            utils.prRed(traceback.format_exc())

    async def timer_trust_role(self):
        utils.prGreen("Updating trust level role")
        for guild in list(self.bot.guilds):
            await self.update_role(guild)

    async def timer_update_ID(self):
        utils.prGreen("updating ID for discourse")
        for guild in list(self.bot.guilds):
            await self.get_update_id(guild.id)

    async def timer(self):
        for guild in list(self.bot.guilds): #start checking new thread and post.
            log.debug("Checking guild {}".format(repr(guild)))
            self.bg_dis.current = datetime.datetime.utcnow() #let see if it work that way,
            await self.new_post(guild.id)



#########################################################################
#     _____                                                       _     #
#    / ____|                                                     | |    #
#   | |        ___    _ __ ___    _ __ ___     __ _   _ __     __| |    #
#   | |       / _ \  | '_ ` _ \  | '_ ` _ \   / _` | | '_ \   / _` |    #
#   | |____  | (_) | | | | | | | | | | | | | | (_| | | | | | | (_| |    #
#    \_____|  \___/  |_| |_| |_| |_| |_| |_|  \__,_| |_| |_|  \__,_|    #
#                                                                       #
#########################################################################

    @commands.command(name="summary",brief="Showing a summary of user")
    async def summary_stat(self,ctx,*,name: str): #Showing a summary stats of User
        '''
        Give a stat of summary of that username
        Topics Created:
        Posts Created:
        Likes Given:
        Likes Received:
        Days Visited:
        Posts Read:
        '''
        config =await self.redis.hgetall("{}:Discourse:Config".format(ctx.message.guild.id))
        flag,data = await self.get_data(config,"users/ {}/summary".format(name),ctx.message.guild.id)  #Get info of that users
        if flag == False or data == 404: #If there is error  which can be wrong user
            await self.bot.say(ctx,content = "{} is not found! Please double check case and spelling!".format(name))
            return
        summary=data["user_summary"] #Dict short for print_data format
        print_data= "Topics Created:{0[topic_count]}\n" \
                    "Post Created:{0[post_count]}\n" \
                    "Likes Given:{0[likes_given]}\n" \
                    "Likes Received:{0[likes_received]}\n" \
                    "Days Visited:{0[days_visited]}\n" \
                    "Posts Read:{0[posts_read_count]}".format(summary)
        await self.bot.say(ctx,content = "```xl\n{}\n```".format(print_data))

    @commands.command(name="stats",brief="Show a Site Statistics")
    async def statistics(self,ctx): #To show a stats of website of what have been total post, last 7 days, etc etc
        '''
        Show a table of Topics,Posts, New Users, Active Users, Likes for All Time, Last 7 Days and Lasts 30 Days
        '''
        config =await self.redis.hgetall("{}:Discourse:Config".format(ctx.message.guild.id))
        flag,data=await self.get_data(config,"about",ctx.message.guild.id) #Read files from link Main page/about
        if flag == False: return await self.bot.say("Unable to get data, there is a problem with site")
        stat=data["about"]["stats"]
        x = PrettyTable()
        x.field_names = [" ","All Time","Lasts 7 Days","Last 30 Days"]
        x.align = 'c'
        x.horizontal_char = '─'

        x.add_row(["Topics",stat["topic_count"],stat["topics_7_days"],stat["topics_30_days"]])
        x.add_row(["Posts",stat["post_count"],stat["posts_7_days"],stat["posts_30_days"]])
        x.add_row(["New Users",stat["user_count"],stat["users_7_days"],stat["users_30_days"]])
        x.add_row(["Active Users","",stat["active_users_7_days"],stat["active_users_30_days"]])
        x.add_row(["Likes",stat["like_count"],stat["likes_7_days"],stat["likes_30_days"]])
        await self.bot.say(ctx,content = "```xl\n{}\n```".format(x.get_string()))

    @commands.command(brief="Give a bio of that user")
    async def bio(self,ctx,name:str):
        """
        Give a info of Username
        Username:
        Total Badge:
        View:
        Join:
            Date:
            Time:
        Bio:
        """
        if " " in name:
            await self.bot.say(ctx,content = "There is space in! There is no such name that have space in! Please Try again!")
            return
        config =await self.redis.hgetall("{}:Discourse:Config".format(ctx.message.guild.id))
        flag,read = await self.get_data(config,"users/{}".format(name),ctx.message.guild.id)
        print(flag,read)
        if flag == False : #If there is error  which can be wrong user
            await self.bot.say(ctx,content = "{} is not found! Please double check case and spelling!".format(name))
            return
        data =read["user"]
        data_array=[]
        data_array.append("**Username**: {}".format(data["username"]))
        if data.get("name","") != "":
            data_array.append("**Name**: {}".format(data["name"]))
        if data.get("title",None) != None:
            data_array.append("**Title**: {}".format(data['title']))
        data_array.append("**Total Badge**: {}".format(data["badge_count"]))
        data_array.append("**View**: {}".format(data["profile_view_count"]))
        data_array.append("**Join**:\n\tDate:{}".format(data["created_at"][:-5].strip().replace("T", " \n\tTime:")))
        bio = data.get("bio_raw")
        if bio:
            if len(bio) >= 1800:
                bio = bio[:1800]+"..."
            data_array.append("**Bio**: \n```\n{}\n```".format(bio))
        await self.bot.say(ctx,content = "\n".join(data_array))

    @commands.command(brief="show Logging of discourse",hidden = True)
    async def dstatus(self,ctx):
        """
        Allow to display a log for this guild, Give you a update current ID.
        """
        data = self.log_error.get(ctx.message.guild.id)
        if data is None:
            await self.bot.say(ctx,content = "I cannot check it at this moment!")
        else:
            embed = discord.Embed()
            embed.add_field(name = "Status", value=data["status"])
            embed.add_field(name = "ID", value = "[{0[id]}]({0[link]})".format(data))
            embed.timestamp = data["time"]
            await self.bot.say(ctx,embed=embed)

def setup(bot):
    bot.add_cog(Discourse(bot))
