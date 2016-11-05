from discord.ext import commands
from .utils import utils
from xml.etree import ElementTree
import aiohttp
import html

def synopis(term):
    term = html.unescape(term)
    if len(term) >= 1500:
        return term[:1500]+"..."
    return term

class Myanimelist():
    """
    Is able to search the database of Myanimelist.com to get info about a certain anime/manga
    """

    def __init__(self, bot):
        self.bot = bot
        self.redis = bot.db.redis
        self.bot.say_edit = bot.says_edit

    async def get_data(self, category, name):
        with aiohttp.ClientSession(auth=aiohttp.BasicAuth(login=utils.secret["MAL_USERNAME"],
                                                          password=utils.secret["MAL_PASSWORD"])) as session:
            async with session.get('http://myanimelist.net/api/{}/search.xml?q={}'.format(category, name)) as resp:
                return (await resp.read())

    async def check_status(self,name):
        with aiohttp.ClientSession() as session:
            async with session.get("http://myanimelist.net/malappinfo.php?u={}&status=all".format(name)) as resp:
                if resp.status == 200:
                    xml_data = ElementTree.fromstring(await resp.text())
                    data = dict(zip(['user_id', 'username', 'watching', 'completed', 'on_hold', 'dropped', 'ptw','days_spent_watching'], [x.text for x in xml_data[0]]))
                    if data:
                        total_watch = 0
                        mean_score = 0
                        mean_count =0
                        for x in xml_data:
                            if mean_count == 0:
                                mean_count =+ 1
                                continue
                            total_watch += int(x[10].text)
                            if int(x[13].text) >= 1:
                                mean_score += int(x[13].text)
                                mean_count +=1
                        mean_score = mean_score/(mean_count-1)
                        mean_score = round(mean_score,ndigits=2)
                        data.update({"mean":mean_score,"total_ep":total_watch})
                        return data
                    else:
                        await self.bot.says_edit("This username does not exist!")

    async def data(self, ctx, category, name):
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
            name_data.append("{}. {}".format(count, x("title"))) #So user can see what are in list and called them
            if x("end_date") == "0000-00-00":  # check if there is end date,it will give 0000-00-00 if anime/manga is still airing/publishing
                end_date = "???"
            else:
                end_date = x("end_date")
            link = "http://myanimelist.net/{}/{}".format(category, x("id"))
            if category == "anime":  # Check which category that user ask for
                data.append(
                    "{}\n**Name**: {}\n**Episodes**: {}\n"
                    "**Score**: {}\n**Status**:{}"
                    "\n**Aired**: {} to {}\n**Synopis**:```{}```".format(
                        link, x("title"), x("episodes"), x("score"),x("status"), x("start_date"), end_date,
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
            answer = await self.bot.wait_for_message(timeout=15, author=ctx.message.author, check=digit_check)
            try:
                await self.bot.delete_message(asking)
                await self.bot.delete_message(answer)
            except:
                pass
            if answer is None:  # if user didnt reply any or not, it will print this
                await self.bot.says_edit("You took too long, try again!")
                return
            elif int(answer.content) <= len(
                    data):  # Check if it below in list range so it dont split out of error about out of range
                await self.bot.says_edit(data[int(answer.content) - 1])
            else:
                await self.bot.says_edit("You entered a number that is out of range!")

    @commands.command(brief="Is able to acquire anime info from the Myanimelist database",pass_context=True)
    async def anime(self, ctx, *, name: str):
        """
        Is able to give you the data of an anime from Myanimelist
        <Link>
        Name:
        Episodes:
        Score:
        Status:
        Aired:
        Synopis:
        """
        link_name = name.replace(" ", "_").lower()  # In case there is more than 1 word
        await self.data(ctx, "anime", link_name)

    @commands.command(brief="Is able to acquire manga info from the Myanimelist database",pass_context=True)
    async def manga(self, ctx, *, name: str):
        """
        Is able to give you the data of a Manga from Myanimelist
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
        await self.data(ctx, "manga", link_name)

    async def check_username(self,ctx,name,site):
        boolean = False
        mention = False
        user = ctx.message.author.id
        if ctx.message.mentions: #If mention is true, it will get from mention ID instead.
            user = ctx.message.mentions[0]
            user = user.id
            mention = True
        setting = await self.redis.hget("Profile:{}".format(user),"myanimelist")
        if name is None:
            if setting is None:
                await self.bot.says_edit("You need to enter a name! Or you can enter your own name on your profile at <http://nurevam.site>")
            else:
                boolean = True
                name = setting
        else:
            if mention:
                if setting is None:
                    await self.bot.says_edit("{} didn't register on Nurevam.site yet! Tell him/her do it!".format(ctx.message.mentions[0].display_name))
                else:
                    if await self.check_status(setting):
                        name = setting
                        boolean = True
            else:
               if await self.check_status(name):
                   boolean = True
        if boolean:
            data = await self.check_status(name)
            stats = "Watching:{}\nCompleted:{}\nOn Hold:{}\n" \
                    "Dropped:{}\nPlan To Watch:{}\nTotal Days Watched:{}\n" \
                    "Total Episode Watched:{}\nMean Score:{}".format(data["watching"],data["completed"],data["on_hold"],
                                                                     data["dropped"],data["ptw"],data["days_spent_watching"],
                                                                     data["total_ep"],data["mean"])
            await self.bot.says_edit("```xl\n{}\n```\n<http://myanimelist.net/{}/{}>".format(stats,site,name))

    @commands.command(pass_context=True,brief="link out MAL user's profile")
    async def mal(self,ctx,name = None):
        """
        Is able to link a MAL Profile.
        If you enter your username on your profile on the Nurevam site, Nurevam will automatically link your profile.
        """
        await self.check_username(ctx,name,"profile")


    @commands.command(name="list",pass_context=True,brief = "link out MAL user's anime or manga list")
    async def show_list(self,ctx,_type,name=None):
        """
        Is able to give you the anime/manga list of a user.
        !list amime <username>
        !list manga <username>
        username is optional, if you have entered  your name on nurevam.site, it will print yours.
        If you mention someone, who is registered on nurevam.site, it will give out his.
        """
        if _type == "anime":
            await self.check_username(ctx,name,"animelist")
        elif _type == "manga":
            await self.check_username(ctx,name,"mangalist")
        else:
            await self.bot.says_edit("Please double check what you typed, it is **anime** or **manga**")

def setup(bot):
    bot.add_cog(Myanimelist(bot))
