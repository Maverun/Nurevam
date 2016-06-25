from discord.ext import commands
from .utils import utils
from xml.etree import ElementTree
import aiohttp

def synopis(term):
    if len(term) >= 1500:
        return term[:1500]+"..."
    else:
        return term

def is_enable(msg): #Checking if cogs' config for this server is off or not
    return utils.is_enable(msg, "anime")

class Myanimelist():
    """
    Allow to search up database of Myanimelist.com to see a info of that certain anime/manga
    """

    def __init__(self, bot):
        self.bot = bot
        self.redis = bot.db.redis
        self.bot.say_edit = bot.says_edit

    async def get_data(self, category, name):
        with aiohttp.ClientSession(auth=aiohttp.BasicAuth(login=utils.OS_Get("MAL_USERNAME"),
                                                          password=utils.OS_Get("MAL_PASSWORD"))) as session:
            async with session.get('http://myanimelist.net/api/{}/search.xml?q={}'.format(category, name)) as resp:
                return (await resp.read())

    async def data(self, msg, category, name):
        data = await self.get_data(category, name)
        try:
            root = ElementTree.fromstring(data)
        except:
            await self.bot.say("{} does not exist!".format(name.replace("_"," ")))
            return
        name_data = []
        data = []
        count = 0
        for tag in root:
            count += 1
            x = tag.findtext  # so it can be easy to call it
            name_data.append("{}. {}".format(count, x("title")))
            if x(
                    "end_date") == "0000-00-00":  # check if there is end date,it will give 0000-00-00 if anime/manga is still airing/publishing
                end_date = "???"
            else:
                end_date = x("end_date")
            link = "http://myanimelist.net/{}/{}".format(category, x("id"))
            if category == "anime":  # Check which category that user ask for
                data.append(
                    "{}\n**Name**: {}\n**Episodes**: {}\n**Score**: {}\n**Status**:{}\n**Aired**: {} to {}\n**Synopis**:```{}```".format(
                        link, x("title"), x("episodes"), x("score"), x("status"), x("start_date"), end_date,
                        synopis(x("synopsis")).replace("<br />", "")))
            elif category == "manga":
                if int(x("chapters")) > 0:
                    chapt = "**Volume**:{}\n**Chapter**:{}\n".format(x("volumes"), x("chapters"))
                else:
                    chapt = ""
                data.append(
                    "{}\n**Name**: {}\n{}**Score**: {}\n**Status**: {}\n**Published**: {} to {}\n**Synopis**:```{}```".format(
                        link, x("title"), chapt, x("score"), x("status"), x("start_date"), end_date,
                        synopis(x("synopsis")).replace("<br />", "")))
        if len(root) == 1:
            await self.bot.say("".join(data))
        else:  # if there is more than one of data, it will ask user which one do they want
            def digit_check(num):  # to ensure that answer is int
                return num.content.isdigit()
            asking = await self.bot.say("```{}```\nWhich number?".format("\n".join(name_data)))
            answer = await self.bot.wait_for_message(timeout=15, author=msg.message.author, check=digit_check)
            await self.bot.delete_message(asking)
            await self.bot.delete_message(answer)
            if answer is None:  # if user didnt reply any or not, it will print this
                await self.bot.says_edit("You took too long, try again!")
                return
            elif int(answer.content) <= len(
                    data):  # Check if it below in list range so it dont split out of error about out of range
                await self.bot.says_edit(data[int(answer.content) - 1])
            else:
                await self.bot.says_edit("You enter a number that is out of range!")

    @commands.check(is_enable)
    @commands.command(name="anime", brief="Allow to search anime info rom Myanimelist database",pass_context=True)
    async def anime(self, msg, *, name: str):
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
        link_name = name.replace(" ", "_").lower()  # In case there is more than 1 word
        await self.data(msg, "anime", link_name)

    @commands.check(is_enable)
    @commands.command(name="manga", brief="Allow to search manga info from Myanimelist database",pass_context=True)
    async def manga(self, msg, *, name: str):
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
        link_name = name.replace(" ", "_").lower()
        await self.data(msg, "manga", link_name)


def setup(bot):
    bot.add_cog(Myanimelist(bot))
