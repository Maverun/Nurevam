from discord.ext import commands
from xml.etree import ElementTree
from .utils import utils
import asyncio
import aiohttp
import discord
import html

def synopis(term):
    term = html.unescape(term.replace("<br />", ""))
    if len(term) >= 1500:
        return term[:1500]+"..."
    return term


class Myanimelist():
    """
    Is able to search the database of Myanimelist.com to get info about a certain anime/manga
    """
    auth = aiohttp.BasicAuth(login=utils.secret["MAL_USERNAME"],password=utils.secret["MAL_PASSWORD"])
    header = {"User-Agent":"Nurevam:https://github.com/Maverun/Nurevam"}

    def __init__(self, bot):
        self.bot = bot
        self.redis = bot.db.redis
        self.bot.say_edit = bot.say

    def __local_check(self,ctx):
        return utils.is_enable(ctx,"myanimelist")

    async def get_data(self, category, name):
        try:
            with aiohttp.ClientSession(auth=self.auth,headers=self.header) as session:
                async with session.get('https://myanimelist.net/api/{}/search.xml?q={}'.format(category, name),headers=self.header) as resp:
                    return (await resp.read())
        except aiohttp.ClientResponseError: # some reason, mal dont return API, just nothing... causing error
            return None

    async def check_status(self,ctx,name):
        with aiohttp.ClientSession() as session:
            async with session.get("https://myanimelist.net/malappinfo.php?u={}&status=all".format(name)) as resp:
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
                        if mean_score != 0:
                            mean_score = mean_score/(mean_count-1)
                            mean_score = round(mean_score,ndigits=2)
                        data.update({"mean":mean_score,"total_ep":total_watch})
                        return data
                    else:
                        await self.bot.say(ctx,"This username does not exist!")

    async def send(self,ctx,data):
        # print(data)
        embed = discord.Embed(description = data[0])
        embed.set_image(url = data[1])
        embed.title = data[2]
        embed.url = data[3]
        if ctx.message.guild.me.colour.value:
            embed.colour = ctx.message.guild.me.colour
        await self.bot.say(ctx,embed=embed)

    async def data(self,ctx,category,name):
        data = await self.get_data(category,name)
        try: #Check if this exist, otherwise, return error
            root = ElementTree.fromstring(data)
        except:
            return await self.bot.say(ctx,content = "{} does not exist!".format(name.replace("_"," ")))
        list_data = []
        data = []
        for index,tag in enumerate(root,start = 1):
            x = tag.findtext #Shortcut to call it
            list_data.append("{}. {}".format(index,x("title"))) #add it to list, so we can show them which one
            #Since airing/publishing will return  0000-00-00 which can confused people, so we are doing this way.
            end_date = "???" if x("end_data") == "0000-00-00" else x("end_date")
            link = "https://myanimelist.net/{}/{}".format(category, x("id"))
            #doing append list within list so that we can do something with synopsis later
            if category == "anime":
                info = "\n**Episodes**: {}\n".format(x("episodes"))
            elif category == "manga":
                info = "\n" if not int(x("chapters")) > 0 else "\n**Volume**:{}\n**Chapter**:{}\n".format(x("volumes"), x("chapters"))
            info += "**Score**: {}\n" \
                   "**Status**: {}\n" \
                   "**Published**: {} to {}\n" \
                   "**Synopsis**: \n{}\n".format(x("score"), x("status"), x("start_date"), end_date,synopis(x("synopsis")))
            data.append([info,x("image"),x("title"),link])
            if len("\n".join(list_data)) >= 1800:
                break
        if len(root) == 1:
            await self.send(ctx,data[0])
        else:  # if there is more than one of data, it will ask user which one do they want
            asking = await ctx.send("```{}```\nWhich number?".format("\n".join(list_data)))

            try:
                answer = await self.bot.wait_for("message",timeout=30, check=lambda msg: msg.content.isdigit() and ctx.message.author == msg.author)
                await answer.delete()
            except asyncio.TimeoutError:#timeout error
                await asking.delete()
                return await self.bot.say(ctx,content = "You took too long, please try again!")
            except:
                pass
            await asking.delete() #bot delete it own msg.

            if int(answer.content) <= len(data): #checking if it below range, so don't split out error
                await self.send(ctx,data[int(answer.content) - 1])
            else:
                return await self.bot.say(ctx,content = "You entered a number that is out of range!")

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
        await self.data(ctx, "anime", name.replace(" ","_").lower())

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
        await self.data(ctx, "manga", name.replace(" ","_").lower())

    async def check_username(self,ctx,name,site):
        boolean = False
        mention = False
        user = ctx.message.author.id

        if ctx.message.mentions: #If mention is true, it will get from mention ID instead.
            user = ctx.message.mentions[0].id
            mention = True
        #checking if user have sign up to nurevam
        setting = await self.redis.hget("Profile:{}".format(user),"myanimelist")

        if name is None:
            if setting is None:
                await self.bot.say(ctx,content = "You need to enter a name! Or you can enter your own name on your profile at <http://nurevam.site>")
            else:
                boolean = True
                name = setting

        else:
            if mention:
                if setting is None:
                    await self.bot.say(ctx,content = "{} didn't register on <http://nurevam.site> yet! Tell him/her do it!".format(ctx.message.mentions[0].display_name))
                else:
                    if await self.check_status(ctx,setting):
                        name = setting
                        boolean = True
            else:
               if await self.check_status(ctx,name):
                   boolean = True

        if boolean:
            data = await self.check_status(ctx,name)
            stats = "Watching:{}\nCompleted:{}\nOn Hold:{}\n" \
                    "Dropped:{}\nPlan To Watch:{}\nTotal Days Watched:{}\n" \
                    "Total Episode Watched:{}\nMean Score:{}".format(data["watching"],data["completed"],data["on_hold"],
                                                                     data["dropped"],data["ptw"],data["days_spent_watching"],
                                                                     data["total_ep"],data["mean"])
            await self.bot.say(ctx,content = "```xl\n{}\n```\n<https://myanimelist.net/{}/{}>".format(stats,site,name))

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
            await self.bot.say(ctx,content = "Please double check what you typed, it is **anime** or **manga**")



def setup(bot):
    bot.add_cog(Myanimelist(bot))
