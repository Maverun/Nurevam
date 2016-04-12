from discord.ext import commands
from .Utils import Read
from lxml import etree
import aiohttp

def Setup():
    global Command
    global Roles
    global Config
    Config = Read.config
    Command=Read.Bot_Config["Cogs"]["Myanimelist"] #command so it is easier to call it
    Roles = Read.Bot_Config["Roles"] #Role for permission, so it is easier to call it

class Myanimelist():
    """
    Allow to search up database of Myanimelist.com to see a info of that certain anime/manga
    """
    def __init__(self,bot):
        self.bot = bot

    Setup()

    async def Get_data(self,category,name):
        with aiohttp.ClientSession(auth=aiohttp.BasicAuth(login=Config["MAL Username"],password=Config["MAL Password"])) as session:
            async with session.get('http://myanimelist.net/api/{}/search.xml?q={}'.format(category,name)) as resp:
                return (await resp.read())

    async def Data(self,msg,category,name):
        data = await self.Get_data(category,name)
        try:
            root = etree.fromstring(data)
        except etree.XMLSyntaxError:
            await self.bot.say("{} does not exist!".format(name))
            return
        name_data=[]
        data=[]
        count=0
        for tag in (root):
            count+=1
            x=tag.findtext #so it can be easy to call it
            name_data.append("{}. {}".format(count,x("title")))
            if x("end_date") == "0000-00-00": #check if there is end date,it will give 0000-00-00 if anime/manga is still airing/publishing
                end_date = "???"
            else:
                end_date=x("end_date")
            link ="http://myanimelist.net/{}/{}".format(category,x("id"))
            if category == "anime":#Check which category that user ask for
                data.append("{}\n**Name**: {}\n**Episodes**: {}\n**Score**: {}\n**Status**:{}\n**Aired**: {} to {}\n**Synopis**:```{}```".format(link,x("title"),x("episodes"),x("score"),x("status"),x("start_date"),end_date,x("synopsis").replace("<br />","")))
            elif category == "manga":
                if int(x("chapters")) > 0:
                    chapt="**Volume**:{}\n**Chapter**:{}\n".format(x("volumes"),x("chapters"))
                else:
                    chapt=""
                data.append("{}\n**Name**: {}\n{}**Score**: {}\n**Status**: {}\n**Published**: {} to {}\n**Synopis**:```{}```".format(link,x("title"),chapt,x("score"),x("status"),x("start_date"),end_date,x("synopsis").replace("<br />","")))
        if len(root) == 1:
            await self.bot.say("".join(data))
        else: #if there is more than one of data, it will ask user which one do they want
            def digit_check(num): #to ensure that answer is int
                return num.content.isdigit()
            await self.bot.say("```{}```\nWhich number?".format("\n".join(name_data)))
            answer = await self.bot.wait_for_message(timeout=15,author=msg.message.author,check=digit_check)
            if answer is None: #if user didnt reply any or not, it will print this
                await self.bot.say("You took too long, try again!")
                return
            elif int(answer.content) <= len(data): #Check if it below in list range so it dont split out of error about out of range
                await self.bot.say(data[int(answer.content)-1])
            else:
                await self.bot.say("You enter a number that is out of range!")

    @commands.command(name=Command["Anime"],brief="Allow to search anime and give info of it from Myanimelist database",pass_context=True)
    async def Anime(self,msg,*,name:str):
        """
        Allow to give you a infomatives of Anime from Myanimelist
        <Link>
        Name:
        Episodes:
        Score:
        Status:
        Aired:
        Synopis:
        """
        link_name=name.replace(" ","_") #In case there is more than 1 word
        await self.Data(msg,"anime",link_name)


    @commands.command(name=Command["Manga"],brief="Allow to search manga and give info of it from Myanimelist database",pass_context=True)
    async def Manga(self,msg,*,name:str):
        """
        Allow to give you a infomatives of Manga from Myanimelist
                Allow to give you a list of Anime from data base
        <Link>
        Name:
        Volume:
        Score:
        Status:
        Published:
        Synopis:
        """
        link_name = name.replace(" ","_")
        await self.Data(msg,"manga",link_name)

def setup(bot):
    bot.add_cog(Myanimelist(bot))