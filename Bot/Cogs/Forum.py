from discord.ext import commands
from .Utils import Read
import asyncio
import aiohttp

def Setup():
    global Config
    global Command
    global Roles
    global website
    Config= Read.config #Config.json files
    Command=Read.Bot_Config["Cogs"]["Forum"] #command so it is easier to call it
    Roles = Read.Bot_Config["Roles"] #Role for permission, so it is easier to call it
    website = Config["link"] #Main website link

async def APIKey():
    key=Config["API Key"]
    username=Config["API Username"]
    return "?api_key={}&api_username={}".format(key,username)

async def Readlinkjson(name): #read a link and then covert them into json
    api = await APIKey()
    with aiohttp.ClientSession() as session:
        async with session.get(website+name+".json"+api) as resp:
            return(await resp.json())
class Forum():
    """
    Forum of Discourse
    Command here.
    """
    def __init__(self, bot):
        self.bot = bot
        loop = asyncio.get_event_loop()
        loop.create_task(self.fetch_latest_in_background())
    Setup()

    async def fetch_latest_in_background(self):#Run to check if there any new post
        try:
            await self.latest()
        finally:
            loop = asyncio.get_event_loop()
            loop.call_later(Config["Second"], lambda: loop.create_task(self.fetch_latest_in_background()))

    async def latest(self): #Checking if there is new post
        """
        Check if there is any new thread.
        If there is, then add them into a list
        using format of this way
        <Titles>  Author:<Creator>
        <link>

        Note: it will also ignore pinned one if pinned thread is only one post.
        It check if there is no replies, then it is as "new thread"
        """
        Data= []
        old_data= await Read.ReadFiles('','Latest.json')
        json_data= await Readlinkjson("/latest")#calling function that will read link json
        for key in json_data["topic_list"]["topics"]:#for each of "latest" titles
            if key["title"] in old_data and key["id"] == old_data[key["title"]]: #if it already exist, then skip
                continue
            if key["posts_count"] == 1: #checking if post itself is only creator, which will show as "new thread"
                json_post=await Readlinkjson("/t/{}".format(key['id']))
                for post_data in json_post["post_stream"]["posts"]:
                    if post_data["post_number"]==1: #Out of all post, it will get creator username
                        Data.append("{} \tAuthor:{} \n{}\n".format(key["title"],post_data["username"],website+"/t/"+key["slug"]+"/"+str(key['id'])))
                        old_data.update({key["title"]:key["id"]}) #It will write to files later on so it can check if it already exist and still no replies, poor original poster...
                        print(key["title"],post_data["username"],key["id"])
                        print("#############################################################")
                        break
        await Read.InputFiles(old_data,"","Latest.json") #Reason for Json/Dict, beacuse in case of Titles are same name but creator may be different
        print("".join(Data))
        if len("".join(Data)) == 0:
            print ("return")
            return
        elif len("".join(Data)) >=5:
            print("send")
            await self.bot.send_message(self.bot.get_channel(Config["Data Channel"]),"".join(Data))

    @commands.command(name = Command["Timer"],brief="Allow to change timer for bot checking thread and post.",pass_context= True)
    @commands.has_any_role(*Roles)
    async def Timer(self,msg,*,second:int): #To change a time
        """
        Change time for bot to regular update.
        Note: Use a Second.
        Also it will take it effect after last timer up.
        For example, timer was 10 min
        now you enter !time 300
        which is 5 min, but you have to wait 10 min or w/e remain min since last post. Once it done, it will replace with 5 min.
        """
        Config.update({"Second":int(second)})
        await Read.InputFiles(Config,"","Config.json")
        if int(second) <=60:
            await self.bot.say("It is now updated. You have enter {} second".format(second))
        else:
            min = int(second)/60
            await self.bot.say("It is now updated. You have enter {} second, which is {} min".format(second, format(min,'.2f')))

    @commands.command(name=Command["Summary_Stat"],brief="Showing a summary of user",pass_context= True)
    async def Summary_stat(self,msg,*,name: str): #Showing a summary stats of User
        '''
        Give a stat of summary of that username
        Topics Created:
        Posts Created:
        Likes Given:
        Likes Received:
        Days Visited:
        Posts Read:
        '''
        data = await Readlinkjson("/users/{}/summary".format(name))  #Get info of that users
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

    @commands.command(name=Command["Statictics"],brief="Show a Site Statistics",pass_context=True)
    async def Statictics(self): #To show a stats of website of what have been total post, last 7 days, etc etc
        '''
        Show a table of Topics,Posts, New Users, Active Users, Likes for All Time, Last 7 Days and Lasts 30 Days
        '''
        data=await Readlinkjson("/about") #Read files from link Main page/about
        stat=data["about"]["stats"]
        await self.bot.say("""
        ```py
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

    @commands.command(name=Command["Bio"],brief="Give a bio of that user",pass_context=True)
    async def Bio(self,msg,*,name:str):
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
        read= await Readlinkjson("/users/{}".format(name))
        if "errors" in read: #If there is error  which can be wrong user
            await self.bot.say("{} is not found! Please double check case and spelling!".format(name))
            return
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


    @Summary_stat.error
    @Timer.error
    @Bio.error
    async def search_error(self, error, ctx):
        if isinstance(error, commands.MissingRequiredArgument):
            await self.bot.say("You didn't put info in!")
def setup(bot):
    bot.add_cog(Forum(bot))
