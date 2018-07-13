# from pyanimu import Mal,UserStatus, connectors,error
from pyanimu import connectors,error,Anilist,UserStatus_Anilist
from discord.ext import commands
from xml.etree import ElementTree
from .utils import utils
import asyncio
import aiohttp
import discord
import html

def synopis(term):
    term = html.unescape(term.replace("<br />", ""))
    term = term.replace("[/","[").replace("[b]","**").replace("[i]","_")
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
        self.bot.say_edit = bot.say

        # self.main = Mal(utils.secret["MAL_USERNAME"],utils.secret["MAL_PASSWORD"],connectors.AioAnimu(user_agent="Nurevam:https://github.com/Maverun/Nurevam"))
        self.main_anilist = Anilist(connectors.AioAnimu(user_agent="Nurevam:https://github.com/Maverun/Nurevam"))

    def __local_check(self,ctx):
        return utils.is_enable(ctx,"myanimelist")

    async def search_query(self,ctx,obj,anilist = False):
        """
        Args:
            ctx:discord context
            obj: anime/manga object that can be list or not

        Returns: obj itself that user asked for
        """
        if anilist:
            obj_data = obj["media"]
            print(obj_data)
            if len(obj_data) == 1:
                return obj_data[0]
            elif bool(obj_data) is True:
                data = ["{}. {}".format(index,name) for index,name in enumerate([x["title"]["romaji"] for x in obj_data],start = 1)]#wew lad
                answer = await utils.input(self.bot,ctx,"```{}```\nWhich number?".format("\n".join(data)),lambda msg: msg.content.isdigit() and ctx.message.author == msg.author)#getting input from user
                if int(answer.content) <= len(data): #checking if it below range, so don't split out error
                    return obj_data[int(answer.content) - 1 ]
                else:
                    await self.bot.say(ctx,content = "You entered a number that is out of range!")
            await self.bot.say(ctx, content = "I cannot find what you are asking for.")
            return None
        
        if isinstance(obj,list): #if it list then we must do something about it such as asking user which one
            data = ["{}. {}".format(index,name) for index,name in enumerate([x.title for x in obj],start = 1)]#wew lad
            answer = await utils.input(self.bot,ctx,"```{}```\nWhich number?".format("\n".join(data)),lambda msg: msg.content.isdigit() and ctx.message.author == msg.author)#getting input from user
            if int(answer.content) <= len(data): #checking if it below range, so don't split out error
                return obj[int(answer.content) - 1 ]
            else:
                await self.bot.say(ctx,content = "You entered a number that is out of range!")
                return None
        return obj

    async def show_anime_mal(self, ctx, obj, category):
        """
        This is for showing anime info and can update/add anime for you.
        Args:
            ctx: Discord Context
            obj: pyanimu.Anime or pyanime.Manga object
            category: int of 0 or 1, 0 is anime, 1 is manga

        It will create format for embeds and have team pick reaction they want.to add to list.

        """
        obj.category = category
        embed = discord.Embed(title = obj.title,url = "https://myanimelist.net/{}/{}".format("anime" if category == 0 else "manga", obj.id))
        embed.set_image(url = obj.image)
        text = ""
        if category == 0: #anime
            text +="**Episode:** {0.episodes}\n"
            embed.set_footer(text="[W]atching | [P]lan to | [C]ompleted | \U0001f5d1 Remove | \U00002753 Seen this?")
            reaction_list = [["\U0001f1fc", self.watching_mal]]  #for Remove, will think about it
        else: #manga
            text +="**Chapter:** {0.chapters}\n**Volumes:**: {0.volumes}\n"
            embed.set_footer(text="[R]eading | [P]lan to | [C]ompleted | \U0001f5d1 Remove | \U00002753 Seen this?")
            reaction_list = [["\U0001f1f7", self.watching_mal]]  #for Remove, will think about it
        #rest of reaction list to add
        reaction_list += [["\U0001f1f5", self.planning_mal], ["\U0001f1e8", self.complete_mal], ["\U0001f5d1", self.remove_mal], ["\U00002753", self.seen_this_mal]]
        text += "**Score:** {0.score}\n**Status:** {0.status}\n**Type:** {0.type}\n**Published:** {1}\n**Synopsis:** {2}"
        embed.description = text.format(obj,"{0.start_date} to {0.end_date}".format(obj),synopis(obj.synopsis))

        def check(reaction,user):#checking conditions
            if reaction.message.id == data.message.id and user.bot is False:
                return bool(str(reaction.emoji) in ["\U0001f1fc","\U0001f1f5","\U0001f1e8","\U0001f1f7","\U0001f5d1","\U00002753"])
            return False
        #Start making embed system,and have user click reaction for function.
        data = utils.Embed_page(self.bot,[embed],reaction = reaction_list)
        await data.start(ctx.message.channel,check = check,timeout = 40,is_async = True,extra = [obj,ctx])
        #concern about memory leak due to object references, so hope this will help.
        del data
        del obj

    async def show_anime_anilist(self, ctx, data, category):
        """
        This is for showing anime info and can update/add anime for you.
        Args:
            ctx: Discord Context
            data: json of return result.
            category: int of 0 or 1, 0 is anime, 1 is manga

        It will create format for embeds and have team pick reaction they want.to add to list.

        """
        # obj.category = category https://anilist.co/anime/1/Cowboy-Bebop/
        url =  data["siteUrl"]
        mal_url = "https://myanimelist.net/{}/{}".format("anime" if category == 0 else "manga", data["idMal"])
        embed = discord.Embed(title = data["title"]["romaji"],url = url)
        embed.set_image(url = data["coverImage"]["large"])
        text = "[AniList]({}) [MAL]({})\n".format(data["siteUrl"],mal_url)
        utils.prGreen(text)
        date = "{0[startDate][year]}-{0[startDate][month]}-{0[startDate][day]} to {0[endDate][year]}-{0[endDate][month]}-{0[endDate][day]}".format(data)
        #i am making most of values to lower case instead of FINISHED, should be finished etc, doing this way is due to season. lazy sorry i know.
        if category == 0: #anime
            value = [str(x).lower() for x in [data["meanScore"], data["status"], data["format"], date, data["season"]]]
            text += "**Episode:** {0[episodes]}\n**Score:** {2}\n**Status:** {3}\n**Type:** {4}\n**Published:** {5}\n**Season:** {6}\n**ID:** {0[id]}\n**Synopsis:** {1}"

            embed.set_footer(text="[W]atching | [P]lan to | [C]ompleted | \U0001f5d1 Remove | \U00002753 Seen this?")
            reaction_list = [["\U0001f1fc", self.watching_anilist]]
        else: #manga
            value = [str(x).lower() for x in [data["meanScore"], data["status"], data["format"], date]]
            text += "**Chapter:** {0[chapters]}\n**Volumes:**: {0[volumes]}\n**Score:** {2}\n**Status:** {3}\n**Type:** {4}\n**Published:** {5}\n**ID:** {0[id]}\n**Synopsis:** {1}"

            embed.set_footer(text="[R]eading | [P]lan to | [C]ompleted | \U0001f5d1 Remove | \U00002753 Seen this?")
            reaction_list = [["\U0001f1f7", self.watching_anilist]]

        #rest of reaction list to add
        reaction_list += [["\U0001f1f5", self.planning_anilist], ["\U0001f1e8", self.complete_anilist], ["\U0001f5d1", self.remove_anilist], ["\U00002753", self.seen_this_anilist]]

        embed.description = text.format(data,synopis(data["description"]),*value)

        def check(reaction,user):#checking conditions
            if reaction.message.id == data_embed.message.id and user.bot is False:
                return bool(str(reaction.emoji) in ["\U0001f1fc","\U0001f1f5","\U0001f1e8","\U0001f1f7","\U0001f5d1","\U00002753"])
            return False
        #Start making embed system,and have user click reaction for function.
        data_embed = utils.Embed_page(self.bot,[embed],reaction = reaction_list)
        await data_embed.start(ctx.message.channel,check = check,timeout = 40,is_async = True,extra = [data,ctx])
        #concern about memory leak due to object references, so hope this will help.
        del data_embed
        del data

    async def verify_account(self,ctx,user):
        """

        Args:
            ctx:discord context
            user: discord member obj

        Returns:

        """
        #Checking if user have abuse api call over 5 time
        cd = await self.redis.get("Myanimelist:Abuse:{}".format(user.id))
        if cd and cd >= 5:
            await ctx.send("I am sorry, I cannot do it for you at this moment, you have done over 5 failed attempt. Please wait for next day, and double check account details at <https://nurevam.site/profile/profile>",delete_after = 10)
            return None
        #Getting setting for username or password
        setting = await self.redis.hgetall("Profile:{}".format(user.id))
        username = setting.get("myanimelist")
        password = setting.get("myanimelist_password")
        if not(username and password): #if there is no password or
            await ctx.send("You need username and password for it! Enter info in there <https://nurevam.site/profile/profile>",delete_after = 10)
            return None

        account = Mal(username,password,connectors.AioAnimu(user_agent="Nurevam:https://github.com/Maverun/Nurevam"))  #create account object
        is_verify = await account.verify() #ensuring it is verify
        if is_verify:
            return account
        else:
            await ctx.send("There is something wrong with your myanimelist account. Please double check username,password at <https://nurevam.site/profile/profile>",delete_after = 10)
            await self.redis.incr("Myanimelist:Abuse:{}".format(user.id))
            await self.redis.expire("Myanimelist:Abuse:{}".format(user.id),86400)#A day.

    async def add_to_list(self,account,obj):
        try:
            await account.add(obj)
            return True
        except error.Http_denied as e:
            if "already in the list." in e.content:
                try:
                    await account.update(obj)
                    return True
                except Exception as err:
                    utils.prRed(err)
        except Exception as e:
            utils.prRed(e)
        return False

    async def watching_mal(self, *args):
        react,member,obj,ctx = args
        account = await self.verify_account(ctx,member)
        if account is None: return
        obj.user_status = UserStatus.watching #same with manga as well
        status = await self.add_to_list(account,obj)
        utils.prCyan(status)
        if status:
            await ctx.send("{}, I have added {} to your watching/reading list".format(member.mention, obj.title),delete_after = 10)

    async def planning_mal(self, *args):
        react,member,obj,ctx = args
        account = await self.verify_account(ctx,member)
        if account is None: return
        obj.user_status = UserStatus.plantowatch #same with manga as well
        status = await self.add_to_list(account, obj)
        utils.prCyan(status)
        if status:
            await ctx.send("{}, I have added {} to your plan to list".format(member.mention, obj.title),delete_after = 10)

    async def complete_mal(self, *args):
        react,member,obj,ctx = args
        account = await self.verify_account(ctx,member)
        if account is None: return
        obj.user_status = UserStatus.completed #same with manga as well
        if obj.category == 0:
            obj.current_episode = obj.episodes
        else:
            obj.read_chapters = obj.chapters
            obj.read_volumes = obj.volumes

        asking = await ctx.send("Rate it from 1-10, 0 for no rate.")
        # now we will ask user to rate it.
        answer = await utils.input(self.bot,ctx, "Rate it from 1-10, 0 for no rate.",lambda msg: msg.content.isdigit() and ctx.message.author == msg.author and int(msg.content) >= 0 and int(msg.content) <= 10)
        rate = int(answer.content)
        if rate != 0:
            obj.user_score = rate
        status = await self.add_to_list(account, obj)
        if status:
            await ctx.send("{}, I have added {} to your finished list".format(member.mention, obj.title),delete_after = 10)

    async def remove_mal(self, *args):
        react,member,obj,ctx = args
        account = await self.verify_account(ctx,member)
        if account is None: return
        await account.delete(obj)
        await ctx.send("{}, I have removed {} from your list".format(member.mention, obj.title),delete_after = 10)

    async def seen_this_mal(self, *args):#checking if user have seen this anime or not
        react, member, obj, ctx = args
        async with ctx.message.channel.typing():#as this expensive work, so user will know bot is working on it
            account = await self.verify_account(ctx, member)
            if account is None: return
            user_data = await account.aio_search_user(account.username)

            #let fun begin...
            data = user_data.anime if obj.category == 0 else user_data.manga
            goal = None
            for x in data:
                if x.title == obj.title:
                    goal = x
                    break
            if goal is None:
                return await ctx.send(content = "You haven't seen this before",delete_after = 10)
            if obj.category == 0:
                text = "**Episodes:** {0.current_episode}/{1.episodes}\n"
            else:
                text = "**Chapters:** {0.read_chapters}/{1.chapters}\n**Volumes:** {0.read_volumes}/{1.volumes}\n"

            text += "**User Score:** {0.user_score}\n**User Status:** {0.user_status}"

            embed = discord.Embed(title=goal.title,url="https://myanimelist.net/{}/{}".format("anime" if obj.category == 0 else "manga",obj.id))
            embed.set_author(name=str(member),icon_url=member.avatar_url)
            embed.description = text.format(goal,obj)
            if member.colour.value:
                embed.colour = member.color
            await self.bot.say(ctx,embed=embed)

    async def anilist_token(self,ctx,member):
        token = await self.redis.hget("Profile:{}:Anilist".format(member.id),"access_token")
        if token:
            account = Anilist(connectors.AioAnimu(),token)
            return account
        await ctx.send("{},I can't do any for you unless you have token, please visit <https://nurevam.site/profile> to get one.".format(member.mention),delete_after = 10)

    async def watching_anilist(self, *args):
        react,member,data,ctx = args
        account = await self.anilist_token(ctx,member)
        if account is None: return
        status = await account.add(data["id"],UserStatus_Anilist.current)
        utils.prCyan(status)
        if status:
            await ctx.send("{}, I have added {} to your watching/reading list".format(member.mention, data["title"]["romaji"]),delete_after = 10)

    async def planning_anilist(self, *args):
        react,member,data,ctx = args
        account = await self.anilist_token(ctx,member)
        if account is None: return
        status = await account.add(data["id"],UserStatus_Anilist.planning)
        utils.prCyan(status)
        if status:
            await ctx.send("{}, I have added {} to your plan to list".format(member.mention, data["title"]["romaji"]),delete_after = 10)

    async def complete_anilist(self, *args):
        react, member, data, ctx = args
        account = await self.anilist_token(ctx, member)

        # now we will ask user to rate it.
        answer = await utils.input(self.bot,ctx, "Rate it from 1-100, 0 for no rate.",lambda msg: msg.content.isdigit() and ctx.message.author == msg.author and int(msg.content) >= 0 and int(msg.content) <= 100)
        rate = int(answer.content)
        extra = {}
        if rate != 0:
            extra["score"] = rate

        status = await account.add(data["id"],UserStatus_Anilist.complete,extra)
        if status:
            await ctx.send("{}, I have added {} to your finished list".format(member.mention, data["title"]["romaji"]),delete_after = 10)

    async def remove_anilist(self, *args):
        react, member, data, ctx = args
        account = await self.anilist_token(ctx, member)
        if account is None: return
        account.toggle_setting(media_list=True)
        if data["type"] == "ANIME":
            get = await account.search_anime(data["id"])
        else:
            get = await account.search_manga(data["id"])

        media_id = get["media"][0]["mediaListEntry"]["id"]
        await account.delete(media_id)
        await ctx.send("{}, I have removed {} from your list".format(member.mention, data["title"]["romaji"]),delete_after = 10)

    async def seen_this_anilist(self, *args):#checking if user have seen this anime or not
        react, member, data, ctx = args
        async with ctx.message.channel.typing():#as this expensive work, so user will know bot is working on it
            account = await self.anilist_token(ctx, member)
            if account is None: return
            account.toggle_setting(media_list=True)
            if data["type"] == "ANIME":
                get = await account.search_anime(data["id"])
            else:
                get = await account.search_manga(data["id"])
            user = get["media"][0]["mediaListEntry"]
            if user is None:
                return await self.bot.say(ctx,content = "{},You haven't seen this one before".format(member.mention))
            if data["type"] == "ANIME":
                text = "**Episodes:** {0[progress]}/{1[episodes]}\n"
            else:
                text = "**Chapters:** {0[progress]}/{1[chapters]}\n**Volumes:** {0[progressVolumes]}/{1[volumes]}\n"

            text += "**User Score:** {0[score]}\n**User Status:** {0[status]}"

            embed = discord.Embed(title=data["title"]["romaji"],url=data["siteUrl"])
            embed.set_author(name=str(member),icon_url=member.avatar_url)
            embed.description = text.format(user,data)
            if member.colour.value:
                embed.colour = member.color
            await self.bot.say(ctx,embed=embed)


    @commands.command(brief="Is able to acquire anime info from the Myanimelist/Anilist database",pass_context=True)
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
        # data = await self.search_query(ctx,await self.main.search_anime(name))
        if name.isdigit():
            name = int(name)#ID work as well.
        data = await self.search_query(ctx,await self.main_anilist.search_anime(name),anilist=True)
        if data is None:return
        await self.show_anime_anilist(ctx, data, 0)


    @commands.command(brief="Is able to acquire manga info from the Myanimelist/Anilist database",pass_context=True)
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
        if name.isdigit():
            name = int(name)
        # data = await self.search_query(ctx,await self.main.search_manga(name))
        data = await self.search_query(ctx,await self.main_anilist.search_manga(name),anilist=True)
        if data is None:return
        await self.show_anime_anilist(ctx, data, 1)

    async def check_username(self,ctx,name,site):
        boolean = False
        mention = False
        user = ctx.message.author

        if ctx.message.mentions: #If mention is true, it will get from mention ID instead.
            user = ctx.message.mentions[0]
            mention = True
        #checking if user have sign up to nurevam
        setting = await self.redis.hget("Profile:{}".format(user.id),"myanimelist")

        if name is None:
            if setting is None:
                await self.bot.say(ctx,content = "You need to enter a name! Or you can enter your own name on your profile at <http://nurevam.site>")
            else:
                boolean = True
                name = setting

        else:
            if mention:
                if setting is None:
                    await self.bot.say(ctx,content = "{} didn't register on <http://nurevam.site> yet! Tell him/her do it!".format(user.display_name))
                else:
                    # if await self.check_status(ctx,setting):
                    name = setting
                    boolean = True
            else:
               # if await self.check_status(ctx,name):
               boolean = True

        if boolean:
            # data = await self.check_status(ctx,name)
            async with ctx.message.channel.typing():
                def cacluate(obj,category):
                    mean_count = 0
                    mean = 0
                    total = 0
                    for x in obj:
                        if int(x.user_score) > 0:
                            mean_count += 1
                            mean += int(x.user_score)
                        total += int(x.current_episode) if category == 0 else int(x.read_chapters)
                    return total,round(mean/mean_count,2)

                data = await self.main.aio_search_user(name)
                total,mean = cacluate(data.anime,0)
                anime_stats = "Watching:{0.anime_watching} \nCompleted:{0.anime_completed} \nOn Hold:{0.anime_onhold} \n" \
                        "Dropped:{0.anime_dropped} \nPlan To Watch:{0.anime_plan_to_watch} \nTotal Days Watched:{0.anime_days} \n" \
                        "Total Episode Watched:{1} \nMean Score:{2} ".format(data,total,mean)
                total, mean = cacluate(data.manga,1)
                manga_stats = "Reading:{0.manga_reading} \nCompleted:{0.manga_completed} \nOn Hold:{0.manga_onhold} \n" \
                              "Dropped:{0.manga_dropped} \nPlan To Watch:{0.manga_plan_to_read} \nTotal Days Watched:{0.manga_days} \n" \
                              "Total Chapters Read:{1} \nMean Score:{2} ".format(data, total, mean)

                embed = discord.Embed(title = "{} profile".format(user.display_name),url = "https://myanimelist.net/{}/{}".format(site,name))
                embed.set_author(name=str(user),icon_url=user.avatar_url)
                embed.add_field(name = "Anime Stats",value=anime_stats)
                embed.add_field(name = "Manga Stats",value=manga_stats)

                if user.colour.value:
                    embed.colour = user.color

                await self.bot.say(ctx,embed=embed)
        # await self.bot.say(ctx,content = "```xl\n{}\n```\n<https://myanimelist.net/{}/{}>".format(stats,site,name))

    # @commands.command(pass_context=True,brief="link out MAL user's profile")
    async def mal(self,ctx,name = None):
        """
        Is able to link a MAL Profile.
        If you enter your username on your profile on the Nurevam site, Nurevam will automatically link your profile.
        """
        await self.check_username(ctx,name,"profile")

    @commands.command(brief = "Link out Anilist user's profile. ID also work")
    async def anilist(self,ctx,name):
        if name.isdigit():
            name = int(name)
        user = await self.main_anilist.search_user(name)
        user = user["users"]
        if len(user) > 1:
            data = ["{}. {}".format(index, name) for index, name in enumerate([x["name"] for x in user], start=1)]  # wew lad
            answer = await utils.input(self.bot, ctx, "```{}```\nWhich number?".format("\n".join(data)), lambda msg: msg.content.isdigit() and ctx.message.author == msg.author)  # getting input from user
            if int(answer.content) <= len(data):  # checking if it below range, so don't split out error
                user  = user[int(answer.content) - 1]
            else:
                return await self.bot.say(ctx, content="You entered a number that is out of range!")
        else:
            user = user[0]

        embed = discord.Embed(title = user["name"],url = user["siteUrl"])
        embed.set_thumbnail(url = user["avatar"]["large"])
        anime_stat = user["stats"]["animeStatusDistribution"]
        anime_text = ""
        for data in anime_stat:
            anime_text += "{0[status]}: {0[amount]}\n".format(data)

        manga_stat = user["stats"]["mangaStatusDistribution"]
        manga_text = ""
        for data in manga_stat:
            manga_text += "{0[status]}:{0[amount]}\n".format(data)

        anime_text += "mean:{0[stats][animeListScores][meanScore]}\nSD:{0[stats][animeListScores][standardDeviation]}".format(user)
        manga_text += "mean:{0[stats][mangaListScores][meanScore]}\nSD:{0[stats][mangaListScores][standardDeviation]}".format(user)
        embed.add_field(name = "Anime Stats",value=anime_text.lower().title())
        embed.add_field(name = "Manga Stats",value=manga_text.lower().title())
        await self.bot.say(ctx,embed = embed)

    @commands.command(brief = "Search character from anime/manga. Database is Anilist")
    async def char(self,ctx,name):
        if name.isdigit():
            name = int(name)
        char = await self.main_anilist.search_character(name)
        char = char["characters"]
        print(char)
        if len(char) > 1:
            data = ["{}. {}".format(index, name) for index, name in enumerate(["{} {}".format(x["name"]["first"],x["name"]["last"]) for x in char], start=1)]  # wew lad
            answer = await utils.input(self.bot, ctx, "```{}```\nWhich number?".format("\n".join(data)), lambda msg: msg.content.isdigit() and ctx.message.author == msg.author)  # getting input from user
            if int(answer.content) <= len(data):  # checking if it below range, so don't split out error
                char  = char[int(answer.content) - 1]
            else:
                return await self.bot.say(ctx, content="You entered a number that is out of range!")
        else:
            char = char[0]
        embed = discord.Embed(title = "{0[first]} {0[last]}".format(char["name"]), url = char["siteUrl"])
        embed.set_thumbnail(url = char["image"]["large"])
        show = ""
        for data in char["media"]["nodes"]:
            show += "ID: {} - Title: {}\n".format(data["id"],data["title"]["romaji"])
        embed.description = show +"\n\n"+ synopis(char["description"])
        await self.bot.say(ctx,embed=embed)

def setup(bot):
    bot.add_cog(Myanimelist(bot))
