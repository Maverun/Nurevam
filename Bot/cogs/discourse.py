from discord.ext import commands
from .utils import utils

import asyncio
import aiohttp

def is_enable(msg): #Checking if cogs' config for this server is off or not
    return utils.is_enable(msg, "discourse")

class Discourse(): #Discourse, a forums types.
    def __init__(self,bot):
        self.bot = bot
        self.redis = bot.db.redis
        print("Starting up Discourse")
        loop = asyncio.get_event_loop()
        loop.create_task(self.timer())
        print("Load")


    async def get_data(self,link,api,username,domain):
        #Using headers so it can support both http/1 and http/2
        #Two replace, one with https and one with http...
        headers = {"Host": domain.replace("http://","").replace("https://","")}
        link = "{}.json?api_key={}&api_username={}".format(link,api,username)
        with aiohttp.ClientSession() as discourse:
            async with discourse.get(link,headers=headers) as resp:
                if resp.status == 200:
                    return [True,await resp.json()]
                else:
                    return [False,resp.status]


    async def post(self,server_id):
        if await self.redis.hget('{}:Config:Cogs'.format(server_id),"discourse") is None:
            return
        utils.prPurple(server_id)
        config = await self.redis.hgetall("{}:Discourse:Config".format(server_id))
        id_post = int(await self.redis.get("{}:Discourse:ID".format(server_id)))
        counter = 0
        data=[]
        bool = False
        while True:
            counter +=1
            get_post = await self.get_data("{}:/t/{}".format(config["domain"],id_post+counter),config['api_key'],config['username'],config['domain'])
            utils.prLightPurple(get_post)
            if get_post[0] is False:
                #Run one more bonus to see if there is new post yet, if not, then it mean it is offical end.
                get_post = await self.get_data("{}:/t/{}".format(config["domain"],id_post+counter+1),config['api_key'],config['username'],config["domain"])
                if get_post[1] == 404:
                    break
                elif get_post[1] == 200 or get_post[1] == 403:
                    continue
            if get_post is None:
                continue
            utils.prYellow(get_post)
            get_post=get_post[1]
            bool = True #so it dont get error if there is empty string, which hence set this true
            data.append("{}\t\tAuthor:{}\n{}".format(get_post['fancy_title'],get_post['details']['created_by']['username'],"{}/t/{}".format(config['domain'],id_post+counter)))
        if bool:
            await self.redis.set("{}:Discourse:ID".format(server_id),id_post+counter)
            await self.bot.send_message(self.bot.get_channel(config["channel"]),"\n".join(data))
            utils.prPurple("\n".join(data))


    async def timer(self):
        utils.prPurple("Starting time")
        while True:
            for server in self.bot.servers:
                await self.post(server.id)
            await asyncio.sleep(10)

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
    @commands.check(is_enable)
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
        data = await self.get_data("{}/users/{}/summary".format(config["domain"],name),config["api_key"],config['username'],config["domain"])  #Get info of that users
        data = data[1]
        if "errors" in data: #If there is error  which can be wrong user
            await self.bot.say("{} is not found! Please double check case and spelling!".format(name))
            return
        summary=data["user_summary"] #Dict short for print_data format
        print_data= "Topics Created:{}\nPost Created:{}\nLikes Given:{}\nLikes Received:{}\nDays Visited:{}\nPosts Read:{}".format(summary["topic_count"],
                                                                                                                                   summary["post_count"],
                                                                                                                                   summary["likes_given"],
                                                                                                                                   summary["likes_received"],
                                                                                                                                   summary["days_visited"],
                                                                                                                                   summary["posts_read_count"])
        await self.bot.say("```py\n{}\n```".format(print_data))

    @commands.command(name="stats",brief="Show a Site Statistics",pass_context=True)
    @commands.check(is_enable)
    async def Statictics(self,ctx): #To show a stats of website of what have been total post, last 7 days, etc etc
        '''
        Show a table of Topics,Posts, New Users, Active Users, Likes for All Time, Last 7 Days and Lasts 30 Days
        '''
        config =await self.redis.hgetall("{}:Discourse:Config".format(ctx.message.server.id))
        data=await self.get_data("{}/about".format(config["domain"]),config["api_key"],config["username"],config["domain"]) #Read files from link Main page/about
        data = data[0]
        stat=data["about"]["stats"]
        await self.bot.say("""
        ```xl
    |--------------|----------|--------------|--------------|
    |              | All Time | Lasts 7 Days | Last 30 Days |
    |--------------|----------|--------------|--------------|
    | Topics       |    {0:<6}|      {1:<8}|     {2:<9}|
    |--------------|----------|--------------|--------------|
    | Posts        |    {3:<6}|      {4:<8}|     {5:<9}|
    |--------------|----------|--------------|--------------|
    | New Users    |    {6:<6}|      {7:<8}|     {8:<9}|
    |--------------|----------|--------------|--------------|
    | Active Users |    —     |      {9:<8}|     {10:<9}|
    |--------------|----------|--------------|--------------|
    | Likes        |    {11:<6}|      {12:<8}|     {13:<9}|
    |--------------|----------|--------------|--------------|
    ```

        """.format(stat["topic_count"],stat["topics_7_days"],stat["topics_30_days"],
                   stat["post_count"],stat["posts_7_days"],stat["posts_30_days"],
                   stat["user_count"],stat["users_7_days"],stat["users_30_days"],
                   stat["active_users_7_days"],stat["active_users_30_days"],
                   stat["like_count"],stat["likes_7_days"],stat["likes_30_days"]))

    @commands.command(name="bio",brief="Give a bio of that user",pass_context=True)
    @commands.check(is_enable)
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
        read= await self.get_data("{}/users/{}".format(config["domain"],name),config["api_key"],config["username"])
        utils.prLightPurple(read)
        if not read: #If there is error  which can be wrong user
            await self.bot.say("{} is not found! Please double check case and spelling!".format(name))
            return
        read= read[0]
        data =read["user"]
        data_array=[]
        data_array.append("**Username**: {}".format(data["username"]))
        if data["name"] != "":
            data_array.append("**Name**: {}".format(data["name"]))
        if data["title"] != None:
            data_array.append("**Title**: {}".format(data['title']))
        data_array.append("**Total Badge**: {}".format(data["badge_count"]))
        data_array.append("**View**: {}".format(data["profile_view_count"]))
        data_array.append("**Join**:\n\tDate:{}".format(data["created_at"][:-5].strip().replace("T", " \n\tTime:")))
        if "bio_raw" in data:
            data_array.append("**Bio**: \n```\n{}\n```".format(data["bio_raw"]))
        await self.bot.say("\n".join(data_array))

def setup(bot):
    bot.add_cog(Discourse(bot))