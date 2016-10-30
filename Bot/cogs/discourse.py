from discord.ext import commands
from .utils import utils
import traceback
import asyncio
import aiohttp
import datetime
import html

def is_enable(msg): #Checking if cogs' config for this server is off or not
    return utils.is_enable(msg, "discourse")

def html_unscape(term):
    return html.unescape(term)

class Discourse(): #Discourse, a forums types.
    def __init__(self,bot):
        self.bot = bot
        self.redis = bot.db.redis
        self.counter= 0
        loop = asyncio.get_event_loop()
        self.loop_discourse_timer = loop.create_task(self.timer())

    def __unload(self):
        self.loop_discourse_timer.cancel()
        utils.prLightPurple("Unloading Discourse")

    async def get_data(self,link,api,username,domain):
        #Using headers so it can support both http/1 and http/2
        #Two replace, one with https and one with http...
        # utils.prCyan("Under get_data, {}".format(link))
        try:
            headers = {"Host": domain.replace("http://","").replace("https://","")}
            link = "{}.json?api_key={}&api_username={}".format(link,api,username)
            with aiohttp.ClientSession() as discourse:
                async with discourse.get(link,headers=headers) as resp:
                    if resp.status == 200:
                        return [True,await resp.json()]
                    else:
                        return [False,resp.status]
        except asyncio.CancelledError: #Just in case here for some reason
            utils.prRed("Under get_data function")
            utils.prRed("Asyncio Cancelled Error")
            return None
        except:
            utils.prRed("Under get_data function")
            utils.prRed(traceback.format_exc())
            return None

    async def post(self,server_id):#TODO, make it look better, Serious.
        if await self.redis.hget('{}:Config:Cogs'.format(server_id),"discourse") is None:
            return
        config = await self.redis.hgetall("{}:Discourse:Config".format(server_id))
        if not (config):
            return
        id_post = await self.redis.get("{}:Discourse:ID".format(server_id))
        if not(id_post):
            return
        id_post=int(id_post)
        counter = 0
        data=[]
        data_bool = False
        while True:
            try:
                counter +=1
                link = "{}/t/{}".format(config['domain'],id_post+counter)
                get_post = await self.get_data(link,config['api_key'],config['username'],config['domain'])
                # utils.prYellow(get_post)
                if get_post is None:
                    return
                if get_post[0] is False: #If there is error return
                    #Run one more bonus to see if there is new post yet, if not, then it mean it is offical end.
                    if get_post[1] == 404 or get_post[1]==410:
                        counter -=1
                        break
                    elif get_post[1] == 200:
                        continue
                    elif get_post[1] == 403:
                        count = await self.redis.get("{}:cooldown:403".format(server_id))
                        # print(count)
                        if count is not None: #If key is atually exists, then check how many time it already got 403
                            if int(count) >= 10:
                                break
                        await self.redis.incr("{}:cooldown:403".format(server_id)) #adding up by 1
                        await self.redis.expire("{}:cooldown:403".format(server_id),10) #add timer by 10 second, recall it will reset timer.
                        continue
                    break

                elif get_post[0] is True:
                    get_post=get_post[1]
                    data_bool = True #so it dont get error if there is empty string, which hence set this true
                    data.append("{2}\t\tAuthor: {0[details][created_by][username]}\n{1}".format(get_post,link,html_unscape(get_post["fancy_title"])))
                else: #Appear this is a reason why it stuck for ever... I think.
                    utils.prRed("Found Nothing in Discourse, returning..")
                    return
            except:
                utils.prRed("Failed to get Discourse site!\n{}".format(config["domain"]))
                Current_Time = datetime.datetime.utcnow().strftime("%b/%d/%Y %H:%M:%S UTC")
                error =  '```py\n{}\n```'.format(traceback.format_exc())
                utils.prRed(error)
                user=self.bot.owner
                if len(error) >2000: #so it can nicely send me a error message.
                    error_1=error[:1900]
                    error_2=error[1900:]
                    await self.bot.send_message(user,"```py\n{}```".format(Current_Time + "\n"+ "ERROR!") + "\n" +  error_1)
                    await self.bot.send_message(user,"```py\n{}```".format(Current_Time + "\n"+ "ERROR!") + "\n" +  error_2)
                else:
                    await self.bot.send_message(user, "```py\n{}```".format(Current_Time + "\n"+ "ERROR!") + "\n" +  error)
                return
        if data_bool:
            try:
                if len("\n".join(data)) >=1500:
                    first= data[:int(len(data)/2)]
                    second = data[int(len(data)/2):]
                    await self.bot.send_message(self.bot.get_channel(config["channel"]),"\n".join(first))
                    await self.bot.send_message(self.bot.get_channel(config["channel"]),"\n".join(second))
                else:
                    await self.bot.send_message(self.bot.get_channel(config["channel"]),"\n".join(data))
                await self.redis.set("{}:Discourse:ID".format(server_id),id_post+counter)
                utils.prLightPurple("\n".join(data))
            except:
                Current_Time = datetime.datetime.utcnow().strftime("%b/%d/%Y %H:%M:%S UTC")
                error =  '```py\n{}\n```'.format(traceback.format_exc())
                await self.bot.send_message(self.bot.owner, "```py\n{}```".format(Current_Time + "\n"+ "ERROR!") + "\n" +  error)
                return

    async def timer(self):
        self.bot.id_discourse += 1
        id_count = self.bot.id_discourse #testing ID of loops, how many time is there that
        utils.prPurple("Starting Discourse Loops time")
        counter_loops = 0
        while True:
            try:
                # utils.prLightPurple("Start loops {}".format(counter_loops))
                if counter_loops == 30:
                    self.counter += 1
                    utils.prPurple("Discourse Loops check! {}-ID:{}".format(self.counter,id_count))
                    counter_loops = 0
                if self.bot.id_discourse != id_count:  # if it dont match, it will return
                    return utils.prRed("{} does not match within ID of {}! Ending this loops now".format(self.bot.id_discourse,id_count))
                self.bot.background.update({"discourse":datetime.datetime.now()})
                for server in self.bot.servers:
                    await self.post(server.id)
                counter_loops += 1
                await asyncio.sleep(30)
                # utils.prLightPurple("Loops done {}".format(counter_loops)) #Temp
            except asyncio.CancelledError:
                utils.prRed("Asyncio Cancelled Error")
                return


#########################################################################
#     _____                                                       _     #
#    / ____|                                                     | |    #
#   | |        ___    _ __ ___    _ __ ___     __ _   _ __     __| |    #
#   | |       / _ \  | '_ ` _ \  | '_ ` _ \   / _` | | '_ \   / _` |    #
#   | |____  | (_) | | | | | | | | | | | | | | (_| | | | | | | (_| |    #
#    \_____|  \___/  |_| |_| |_| |_| |_| |_|  \__,_| |_| |_|  \__,_|    #
#                                                                       #
#########################################################################

    @commands.command(name="summary",brief="Showing a summary of user",pass_context= True)
    async def Summary_stat(self,ctx,*,name: str): #Showing a summary stats of User
        '''
        Give a stat of summary of that username
        Topics Created:
        Posts Created:
        Likes Given:
        Likes Received:
        Days Visited:
        Posts Read:
        '''
        config =await self.redis.hgetall("{}:Discourse:Config".format(ctx.message.server.id))
        link ="{}/users/{}/summary".format(config["domain"],name)
        data = await self.get_data(link,config["api_key"],config['username'],config["domain"])  #Get info of that users
        utils.prGreen(data)
        data = data[1]
        if data == 404: #If there is error  which can be wrong user
            await self.bot.say("{} is not found! Please double check case and spelling!".format(name))
            return
        summary=data["user_summary"] #Dict short for print_data format
        print_data= "Topics Created:{0[topic_count]}\n" \
                    "Post Created:{0[post_count]}\n" \
                    "Likes Given:{0[likes_given]}\n" \
                    "Likes Received:{0[likes_received]}\n" \
                    "Days Visited:{0[days_visited]}\n" \
                    "Posts Read:{0[posts_read_count]}".format(summary)
        await self.bot.say("```xl\n{}\n```".format(print_data))

    @commands.command(name="stats",brief="Show a Site Statistics",pass_context=True)
    async def Statictics(self,ctx): #To show a stats of website of what have been total post, last 7 days, etc etc
        '''
        Show a table of Topics,Posts, New Users, Active Users, Likes for All Time, Last 7 Days and Lasts 30 Days
        '''
        config =await self.redis.hgetall("{}:Discourse:Config".format(ctx.message.server.id))
        data=await self.get_data("{}/about".format(config["domain"]),config["api_key"],config["username"],config["domain"]) #Read files from link Main page/about
        data = data[1]
        stat=data["about"]["stats"]
        await self.bot.say("```xl"
                           "\n┌──────────────┬──────────┬──────────────┬──────────────┐\n"
                           "│              │ All Time │ Lasts 7 Days │ Last 30 Days │"
                           "\n├──────────────┼──────────┼──────────────┼──────────────┤"
                           "\n│ Topics       │{0:^10}│{1:^14}│{2:^14}│"
                           "\n├──────────────┼──────────┼──────────────┼──────────────┤"
                           "\n│ Posts        │{3:^10}│{4:^14}│{5:^14}│"
                           "\n├──────────────┼──────────┼──────────────┼──────────────┤"
                           "\n│ New Users    │{6:^10}│{7:^14}│{8:^14}│"
                           "\n├──────────────┼──────────┼──────────────┼──────────────┤"
                           "\n│ Active Users │    —     │{9:^14}│{10:^14}│"
                           "\n├──────────────┼──────────┼──────────────┼──────────────┤"
                           "\n│ Likes        │{11:^10}│{12:^14}│{13:^14}│"
                           "\n└──────────────┴──────────┴──────────────┴──────────────┘\n```".format(
                   stat["topic_count"],stat["topics_7_days"],stat["topics_30_days"],
                   stat["post_count"],stat["posts_7_days"],stat["posts_30_days"],
                   stat["user_count"],stat["users_7_days"],stat["users_30_days"],
                   stat["active_users_7_days"],stat["active_users_30_days"],
                   stat["like_count"],stat["likes_7_days"],stat["likes_30_days"]))

    @commands.command(name="bio",brief="Give a bio of that user",pass_context=True)
    async def Bio(self,ctx,name:str):
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
            await self.bot.say("There is space in! There is no such name that have space in! Please Try again!")
            return
        config =await self.redis.hgetall("{}:Discourse:Config".format(ctx.message.server.id))
        read= await self.get_data("{}/users/{}".format(config["domain"],name),config["api_key"],config["username"],config["domain"])
        if read[1] == 404: #If there is error  which can be wrong user
            await self.bot.say("{} is not found! Please double check case and spelling!".format(name))
            return
        read= read[1]
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
        if "bio_raw" in data:
            data_array.append("**Bio**: \n```\n{}\n```".format(data["bio_raw"]))
        await self.bot.say("\n".join(data_array))

def setup(bot):
    bot.add_cog(Discourse(bot))
