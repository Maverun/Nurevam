# from pyanimu import Mal,UserStatus, connectors,error
from pyanimu import connectors,error,Anilist,UserStatus_Anilist
from discord.ext import commands
from .utils import utils
import asyncio
import aiohttp
import discord
import base64
import time

import html
def synopis(term):
    if not(bool(term)): return ""
    term = html.unescape(term.replace("<br />", ""))
    term = term.replace("[/","[").replace("[b]","**").replace("[i]","_").replace("<br>","\n")
    if len(term) >= 1500:
        return term[:1500]+"..."
    return term


ordinal = lambda n: "%d%s" % (n, "tsnrhtdd"[(n / 10 % 10 != 1) * (n % 10 < 4) * n % 10::4])  # credit to Gareth from codegof. I like this so.

def query_format(data):
    """
    Function: query format

    Params:
    data: dict of that media entry
    big: length of biggest char
    
    """
    title = data["title"]["romaji"]
    start_year = data["startDate"]["year"] or "????" #if unknown some reason
    end_year = data["endDate"]["year"] or "????" #if still airing 
    type_data = data["format"]
    type_data = type_data.lower() if type_data else "????"
    fmt = f"{title} | {type_data} ({start_year}-{end_year})"
    return fmt

    
#end of the function query format

class Anime(commands.Cog):
    """
    Is able to search the database of Myanimelist.com to get info about a certain anime/manga
    """

    def __init__(self, bot):
        self.bot = bot
        self.redis = bot.db.redis
        self.bot.say_edit = bot.say

        # self.main = Mal(utils.secret["MAL_USERNAME"],utils.secret["MAL_PASSWORD"],connectors.AioAnimu(user_agent="Nurevam:https://github.com/Maverun/Nurevam"))
        self.main_anilist = Anilist(connectors.AioAnimu(user_agent="Nurevam:https://github.com/Maverun/Nurevam"))

    def cog_check(self,ctx):
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
            if len(obj_data) == 1:
                return obj_data[0]
            elif bool(obj_data) is True:
                obj_data = obj_data[:25] #Getting only within 25 list
                obj_data = sorted(obj_data, key = lambda x:len(x["title"]["romaji"]))
                # data = ["{}. {}".format(index,name for index,name in enumerate([x["title"]["romaji"] + "|" + x["format"] +"|" for x in obj_data],start = 1) if index <= 25]#wew lad
                data = [f"{index:2}. {query_format(raw)}" for index,raw in enumerate(obj_data,start=1)]
                try:
                    answer = await utils.input(self.bot,ctx,"```{}```\nWhich number? (0 for cancel)".format("\n".join(data)),lambda msg: msg.content.isdigit() and ctx.message.author == msg.author)#getting input from user
                    if answer is None: return None
                    if int(answer.content) <= len(data): #checking if it below range, so don't split out error
                        if int(answer.content) == 0:
                            await self.bot.say(ctx,content = "Cancel query")
                            return None
                        return obj_data[int(answer.content) - 1 ]
                    else:
                        await self.bot.say(ctx,content = "You entered a number that is out of range!")
                        return None
                except discord.NotFound as e: 
                    print("HUH",e)
                    return None
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

    async def show_anime_anilist(self, ctx, data, category,extra = None):
        """
        This is for showing anime info and can update/add anime for you.
        Args:
            ctx: Discord Context
            data: json of return result.
            category: int of 0 or 1, 0 is anime, 1 is manga

        It will create format for embeds and have team pick reaction they want.to add to list.


        Extra is somethng for "recursion" function or want to edit its own message.
        self.whatanime_find is currently doing it.
        Since there can be more than 2 result, so purpose of it was to have show other result instead of write whole thing. DRY yo

        """
        url =  data["siteUrl"]
        mal_url = "https://myanimelist.net/{}/{}".format("anime" if category == 0 else "manga", data["idMal"])
        embed = discord.Embed(title = data["title"]["romaji"],url = url)
        embed.set_image(url = data["coverImage"]["large"])
        text = "[AniList]({}) [MAL]({})\n".format(data["siteUrl"],mal_url)
        if data["startDate"]["year"] == None:
            date = "????"
        else:
            date ="{0[startDate][year]}-{0[startDate][month]}-{0[startDate][day]}".format(data)
        if data["endDate"]["year"] == None:
            date += " to ????"
        else:
            date += " to {0[endDate][year]}-{0[endDate][month]}-{0[endDate][day]}".format(data)
        footer = ""
        #i am making most of values to lower case instead of FINISHED, should be finished etc, doing this way is due to season. lazy sorry i know.
        if category == 0: #anime
            value = [str(x).lower() for x in [data["averageScore"], data["status"], data["format"], date, data["season"]]]
            text += "**Episode:** {0[episodes]}\n**Score:** {2}\n**Status:** {3}\n**Type:** {4}\n**Published:** {5}\n**Season:** {6}\n**ID:** {0[id]}"
            if data["nextAiringEpisode"]:
                airing = data["nextAiringEpisode"]
                time = airing["timeUntilAiring"]
                ep = ordinal(airing["episode"])
                if time > 3600:
                    hour = time/3600 #getting hour
                    min = (time%3600)/60 #getting min
                    day = ""
                    if hour >= 24: #if it more than 1 day, then  we will convert it.
                        day = "{} day(s), ".format(int(hour/24))
                        hour = hour % 24
                    air_msg = "{}{} hour(s) and {} min(s) left for {} episode".format(day,int(hour),round(min),ep)
                else:
                    time /= 60
                    air_msg = "{} min(s) left for {} episode".format(round(time,2),ep)
                text += "\n**Next Airing**: {}".format(air_msg)
            text += "\n**Synopsis:** {1}"
            footer = "[W]atching | [P]lan to | [C]ompleted | \U0001f5d1 Remove | \U00002753 Seen this?"
            reaction_list = [["\U0001f1fc", self.watching_anilist]]
        else: #manga
            value = [str(x).lower() for x in [data["meanScore"], data["status"], data["format"], date]]
            text += "**Chapter:** {0[chapters]}\n**Volumes:** {0[volumes]}\n**Score:** {2}\n**Status:** {3}\n**Type:** {4}\n**Published:** {5}\n**ID:** {0[id]}\n**Synopsis:** {1}"

            footer = "[R]eading | [P]lan to | [C]ompleted | \U0001f5d1 Remove | \U00002753 Seen this?"
            reaction_list = [["\U0001f1f7", self.watching_anilist]]
        #rest of reaction list to add
        reaction_list += [["\U0001f1f5", self.planning_anilist], ["\U0001f1e8", self.complete_anilist], ["\U0001f5d1", self.remove_anilist], ["\U00002753", self.seen_this_anilist]]
        if extra:
            reaction_list += [[extra["react"],extra["method"]]]
            footer += extra["footer"]
            msg = extra["msg"]
            extra = extra["args"]
        else:
            msg = None
            extra = []

        embed.description = text.format(data,synopis(data["description"]),*value)
        embed.set_footer(text=footer)
        def check(reaction,user):#checking conditions
            if reaction.message.id == data_embed.message.id and user.bot is False:
                return bool(str(reaction.emoji) in [x[0] for x in reaction_list])
            return False

        #Start making embed system,and have user click reaction for function.
        data_embed = utils.Embed_page(self.bot,[embed],reaction = reaction_list,alt_edit = bool(extra),original_msg=msg)
        try:
            await data_embed.start(ctx.message.channel,check = check,timeout = 40,is_async = True,extra = [data,ctx]+extra)
        except:pass #ignoring trying to delete already gone message.
        #concern about memory leak due to object references, so hope this will help.
        del data_embed
        del data

    async def anilist_token(self,ctx,member):
        token = await self.redis.hget("Profile:{}:Anilist".format(member.id),"access_token")
        if token:
            try:
                account = Anilist(connectors.AioAnimu(),token)
                await account.user() #if it can run it np, then there is no problem with token.
                return account
            except error.Http_denied:
                await ctx.send("{},Your token has expired, please refresh it by authoize it again, please visit <https://nurevam.site/profile> to link it again.".format(member.mention),delete_after = 30)
        else:
            await ctx.send("{},I can't do anything unless it has linked account, please visit <https://nurevam.site/profile> to link it.".format(member.mention),delete_after = 30)

    async def watching_anilist(self, *args):
        if len(args) == 7:
            react,member,msg,data,ctx,list_data,index = args
        else:
            react, member, data, ctx = args
        account = await self.anilist_token(ctx,member)
        if account is None: return
        status = await account.add(data["id"],UserStatus_Anilist.current)
        utils.prCyan(status)
        if status:
            await ctx.send("{}, I have added {} to your watching/reading list".format(member.mention, data["title"]["romaji"]),delete_after = 10)

    async def planning_anilist(self, *args):
        if len(args) == 7:
            react,member,msg,data,ctx,list_data,index = args
        else:
            react, member, data, ctx = args
        account = await self.anilist_token(ctx,member)
        if account is None: return
        status = await account.add(data["id"],UserStatus_Anilist.planning)
        utils.prCyan(status)
        if status:
            await ctx.send("{}, I have added {} to your plan to list".format(member.mention, data["title"]["romaji"]),delete_after = 10)

    async def complete_anilist(self, *args):
        if len(args) == 7:
            react,member,msg,data,ctx,list_data,index = args
        else:
            react, member, data, ctx = args

        account = await self.anilist_token(ctx, member)
        # now we will ask user to rate it.
        answer = await utils.input(self.bot,ctx, "Rate it from 1-100, 0 for no rate.",lambda msg: msg.content.isdigit() and ctx.message.author == msg.author and int(msg.content) >= 0 and int(msg.content) <= 100)
        if answer is None: return
        rate = int(answer.content)
        extra = {}
        if rate != 0:
            extra["score"] = rate

        status = await account.add(data["id"],UserStatus_Anilist.complete,extra)
        if status:
            await ctx.send("{}, I have added {} to your finished list".format(member.mention, data["title"]["romaji"]),delete_after = 10)

    async def remove_anilist(self, *args):
        if len(args) == 7:
            react,member,msg,data,ctx,list_data,index = args
        else:
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
        if len(args) == 7:
            react,member,msg,data,ctx,list_data,index = args
        else:
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
                return await ctx.send(content = "{},You haven't seen this one before".format(member.mention),delete_after = 10 )
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

    async def get_user(self,ctx,name): #this is for anilist command, if name is string. If there is multi result, we get right one and recall it.
        user = await self.main_anilist.search_user(name)
        user = user["users"]
        if len(user) > 1:
            data = ["{}. {}".format(index, name) for index, name in enumerate([x["name"] for x in user], start=1)]  # wew lad
            answer = await utils.input(self.bot, ctx, "```{}```\nWhich number?".format("\n".join(data)), lambda msg: msg.content.isdigit() and ctx.message.author == msg.author)  # getting input from user
            if answer is None: return
            if int(answer.content) <= len(data):  # checking if it below range, so don't split out error
                user  = user[int(answer.content) - 1]
                user = await self.main_anilist.search_user(user["id"])
                user = user["users"][0]
            else:
                return await self.bot.say(ctx, content="You entered a number that is out of range!")
        else:
            user = user[0]
        return user

    async def whatanime_find(self,*args):
        react,member,msg,anime_data,ctx,data,index = args
        length = len(data)
        anime = await self.main_anilist.search_anime(data) #accepts list, it will do magic.
        if length > 1:
            return await self.whatanime_multi(None,None,None,None,ctx,anime,-1)

        return await self.show_anime_anilist(ctx, anime["media"][0],0)

    async def whatanime_multi(self,*args):
        #if there is more than one anime, this will run since we did search_anime early with list, so meaning we got all anime info we can show.
        react,member,msg,anime_data,ctx,anime,index = args

        if anime["pageInfo"]["total"] == index + 1:
            index = 0
        else:
            index += 1

        extra ={"react":"\U00002b07","method": self.whatanime_multi,"footer":"|⬇ Wrong Anime","msg":msg,"args":[anime,index]}
        return await self.show_anime_anilist(ctx, anime["media"][index],0,extra = extra)

#########################################################################
#     _____                                                       _     #
#    / ____|                                                     | |    #
#   | |        ___    _ __ ___    _ __ ___     __ _   _ __     __| |    #
#   | |       / _ \  | '_ ` _ \  | '_ ` _ \   / _` | | '_ \   / _` |    #
#   | |____  | (_) | | | | | | | | | | | | | | (_| | | | | | | (_| |    #
#    \_____|  \___/  |_| |_| |_| |_| |_| |_|  \__,_| |_| |_|  \__,_|    #
#                                                                       #
#########################################################################

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

    @commands.command(brief = "Link out Anilist user's profile. ID also work")
    async def anilist(self,ctx,name = None):

        if name is None:
            account = await self.anilist_token(ctx, ctx.message.author)
            if account is None: return
            user = await account.user()
            user = user["data"]["Viewer"]
        elif bool(ctx.message.mentions):
            account = await self.anilist_token(ctx,ctx.message.mentions[0])
            if account is None: return
            user = await account.user()
            user = user["data"]["Viewer"]
        elif name:
            if name.isdigit():
                name = int(name)
            user = await self.get_user(ctx,name)
        embed = discord.Embed(title = user["name"],url = user["siteUrl"])
        embed.set_thumbnail(url = user["avatar"]["large"])
        anime_stat = user["statistics"]["anime"]
        anime_text = ""
        for data in anime_stat["statuses"]:
            anime_text += "{0[status]}: {0[count]}\n".format(data)

        manga_stat = user["statistics"]["manga"]
        manga_text = ""
        for data in manga_stat["statuses"]:
            manga_text += "{0[status]}:{0[count]}\n".format(data)

        if user["statistics"]["anime"] is not None:
            anime_text += "mean: {0[meanScore]}\nSD: {0[standardDeviation]}".format(anime_stat)
            manga_text += "mean: {0[meanScore]}\nSD: {0[standardDeviation]}".format(manga_stat)

        embed.add_field(name = "Anime Stats",value=anime_text.lower().title())
        embed.add_field(name = "Manga Stats",value=manga_text.lower().title())
        await self.bot.say(ctx,embed = embed)

    @commands.command(brief = "Search character from anime/manga. Database is Anilist")
    async def char(self,ctx,*,name):
        if name.isdigit():
            name = int(name)
        char = await self.main_anilist.search_character(name)
        char = char["characters"]
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

    @commands.command(brief = "What anime is this from.")
    @commands.cooldown(9,60,commands.BucketType.guild)
    async def whatanime(self,ctx,link = None):
        """
        This will help you to find anime that you link sources. This may not be accurate or not.
        It will take a moment. Files has to be less than 1MB sadly.
        """
        headers = {"User-Agent": "https://nurevam.site/", "host": "trace.moe",
                   "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}
        if link is None:
            check = ctx.message.attachments
            if check:
                link = check[0].url
            else:
                return self.bot.say(ctx, content="Please enter a link or attachments")
        async with ctx.message.channel.typing():
            async with aiohttp.ClientSession() as session:
                async with session.get(link) as resp:
                    picture = base64.b64encode(await resp.read())

                # async with session.post("https://trace.moe/api/search", params={"token": utils.secret["whatanime"]},headers=headers, data={"image": {picture}}) as resp:
                async with session.post("https://trace.moe/api/search",headers=headers, data={"image": {picture}}) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        #Since there can be multi of same anime with different time frame.
                        unique_anime = []
                        for x in data["docs"]:
                            id_ = x["anilist_id"]
                            if id_ not in unique_anime:
                                unique_anime.append(id_)
                        await ctx.send("Checking...",delete_after = 2)
                        return await self.whatanime_find(None,None,None,None,ctx,unique_anime,0)

                    elif resp.status == 413:
                        await self.bot.say(ctx, content="I am sorry, but files is too big.")

    async def display_airing(self,ctx,airing):
        #now we will make a list of upcoming airing
        #[Name](url)(ID) episode: n at date
        air_array = []
        current_date = time.localtime().tm_mday
        counter = 0
        #we will mark page so user know what page they are on.
        page = 1
        max = int(len(airing) / 10 + (1 if len(airing) % 10 != 0 else 0))
        text = ""
        for air in airing: #iterate each airing list
            future = time.gmtime(air["airingAt"]) #time it will aired at
            if future.tm_mday == current_date:  #we are checking if it today, if so we will put up how many hours instead of date
                time_air = air["timeUntilAiring"]
                if time_air > 3600:
                    hour = time_air / 3600  # getting hour
                    min = (time_air % 3600) / 60  # getting min
                    air_msg = "{} hour(s) and {} min(s) left".format(int(hour), round(min))
                else:
                    time_air /= 60
                    air_msg = "{} min(s) left".format(round(time_air, 2))
            else:
                air_msg = time.strftime("on %a %Y %b %d %H:%M:%S gmt",future)

            #set up message
            get_id = "({})".format(air["media"]["id"])

            text += "[{0[media][title][romaji]}]({0[media][siteUrl]}) {1} " \
                   "episode: {2} {3}\n\n".format(air,get_id,ordinal(air["episode"]),air_msg)

            counter += 1
            if counter == 10: #every 10, we will add to list but with embed.
                embed = discord.Embed(description = text)
                embed.set_footer(text = "Page: {}/{}".format(page,max))
                air_array.append(embed)
                counter = 0
                page += 1
                text = ""
        if text:
            embed = discord.Embed(description=text)
            air_array.append(embed) #putting leftover in

        #now we will put air_array into it
        if len(air_array) == 1:
            return await ctx.send(embed = air_array[0])

        embed_system = utils.Embed_page(self.bot,air_array)

        def check(reaction,user):#checking conditions
            if reaction.message.id == embed_system.message.id and user.bot is False:
                return bool(str(reaction.emoji) in [x[0] for x in embed_system.reaction])
            return False
        await embed_system.start(ctx.message.channel,check = check)

    @commands.group(brief = "Show info about upcoming Airing")
    async def airing(self,ctx,name = None):
        """
        Data can be name or ID, it will get data from that anime upcoming ep. If name is blank, it will show all anime upcoming airing.
        airing mylist - will show anime airing dated from your list.
        """

        if name is None:
            data = await self.main_anilist.airingSchedules({"airAtG": int(time.time()),"sort":"TIME"})
        elif name == "mylist": #if it "sub command" then we know user want to see airing related to his anime.
            return await self.airing_mylist(ctx)
        else:
            if name.isdigit():
                name = int(name)  # ID work as well.
            data = await self.search_query(ctx, await self.main_anilist.search_anime(name), anilist=True)
            if data is None: return
            data = await self.main_anilist.airingSchedules({"mid":data["id"],"airAtG": int(time.time()),"sort":"TIME"})

        airing = data["airingSchedules"]
        if bool(airing) is False:
            return await self.bot.say(ctx,content = "I am sorry, there is no upcoming airing for this.")

        await self.display_airing(ctx,airing)

    async def airing_mylist(self,ctx):
        #checking if account is verify.
        account = await self.anilist_token(ctx, ctx.message.author)
        if account is None: return

        #Now we get info about user itself
        user = await account.user()
        user = user["data"]["Viewer"]

        #once we get ID from user itself, we can start getting user list and get its current watching list ID
        user = await self.main_anilist.get_user_list({"id":user["id"],"type":"ANIME","status":UserStatus_Anilist.current})
        user = user["data"]["MediaListCollection"]["lists"][0]["entries"]
        get_all_id = [x.get("mediaId") for x in user]

        #geting airing schedules then print out result
        data = await self.main_anilist.airingSchedules({"mid_in":get_all_id,"airAtG":int(time.time()),"sort":"TIME"})
        airing = data["airingSchedules"]
        if bool(airing) is False:
            return await self.bot.say(ctx,content = "I am sorry, you have no upcoming airing in your own watching list..")

        await self.display_airing(ctx,airing)

def setup(bot):
    bot.add_cog(Anime(bot))
