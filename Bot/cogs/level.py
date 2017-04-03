from PIL import Image,ImageDraw,ImageFont,ImageFilter
from discord.ext import commands
from operator import itemgetter
from random import randint
from .utils import utils
import traceback
import datetime
import aiohttp
import logging
import discord
import asyncio
import re
import io

log = logging.getLogger(__name__)

def is_cooldown(msg):
    redis = utils.redis
    config = redis.get("{}:Level:{}:rank:check".format(msg.message.guild.id,msg.message.author.id))
    return not(bool(config))


class Level:
    """
    A level plugins, gain exp when talking.
    """
    def __init__(self,bot):
        self.bot = bot
        self.redis = bot.db.redis
        self.bot.say_edit = bot.say
        self.column = utils.secret["column"] #U mad bro?
        loop = asyncio.get_event_loop()
        self.loop_level_timer = loop.create_task(self.level_reward())

    def __unload(self):
        self.loop_level_timer.cancel()
        utils.prLightPurple("Unloading Level")

    def __local_check(self,ctx):
        return utils.is_enable(ctx,"level")

    #Those will set expire when member leave guild, to get new "space", they have 2 weeks to return, other wise, level data of their will be lost.
    async def on_member_remove(self,member):
        await self.redis.srem("{}:Level:Player".format(member.guild.id),member.id)
        await self.redis.expire("{}:Level:Player:{}".format(member.guild.id,member.id),1209600)#setting expire dated for member, will last for 2 weeks, if there is change, it will stop expire, aka join back in guild

    async def on_member_join(self,member):
        if await self.redis.exists("{}:Level:Player:{}".format(member.guild.id,member.id)):
            await self.redis.persist("{}:Level:Player:{}".format(member.guild.id,member.id))

    async def on_member_update(self,before,after):
        if before.display_name != after.display_name:
            await self.redis.hset("{}:Level:Player:{}".format(after.guild.id,after.id),"Name",after.display_name)

    async def is_ban(self,member):
        if isinstance(member,discord.Member):
            is_ban_member = await self.redis.smembers("{}:Level:banned_members".format(member.guild.id))
            is_ban_role = await self.redis.smembers("{}:Level:banned_roles".format(member.guild.id))
            for role in member.roles:
                if role.id in is_ban_role:
                    return True
            if member.id in is_ban_member:
                return True
        return False

    async def on_message_global(self,msg,xp):
        """
        I should die/feel shame for this.
        """
        if await self.redis.get("Info:Level:Global_cooldown:{}".format(msg.author.id)):  # If it true, return, it haven't cool down yet
            return
        # Setting cooldown, in case somthing happen, it wont increase xp twice while it still affect some reason, such as data slow.
        await self.redis.set("Info:Level:Global_cooldown:{}".format(msg.author.id), 'cooldown', expire=60)
        # If Cooldown expire, Add xp and stuff
        check_exist = msg.author.id in await self.redis.smembers("Info:Level:Player")  # Call of name and ID to get boolean

        if check_exist is False:  # if it False, then it will update a new list for player who wasn't in level record
            await self.redis.sadd("Info:Level:Player",msg.author.id)

        await self.redis.hincrby("Info:Level:Player_Total_XP",msg.author.id,increment = xp)
        return

    async def on_message(self,msg): #waiting for player reply
        if msg.author == self.bot.user or isinstance(msg.channel,discord.DMChannel) or msg.author.bot:
            return
        if int(msg.author.discriminator) == 0000:
            return #Webhook

        log.debug("Got message from user: {0} -  {0.id}".format(msg.author))

        if await self.redis.hget("{}:Config:Cogs".format(msg.guild.id),"level") == "on":
            log.debug("Enable level")
            xp = randint(5,10)

            await self.on_message_global(msg,xp)

            if await self.is_ban(msg.author) is True:
                return

            if msg.channel.id in await self.redis.smembers("{}:Level:banned_channels".format(msg.guild.id)): #a banned channel
                return

            #Getting ID
            player = msg.author.id
            guild = msg.guild.id
            await self.redis.sadd("{}:Level:Player".format(guild),player)
            name = "{}:Level:Player:{}".format(guild,player) #future references for easier to use

            check_id = await self.redis.hget(name,"ID")

            if check_id is None: #some reason ID wasnt found and hence didn't show in table
                await self.redis.hset(name,"ID",player)

            await self.redis.hincrby(name,"Total Message Count",increment = 1)

            if await self.redis.get("{}:Level:{}:xp:check".format(guild,player)):#If it true, return, it haven't cool down yet
                return
            #Setting cooldown, in case something happen, it wont increase xp twice while it still affect some reason, such as data being slow.
            await self.redis.set("{}:Level:{}:xp:check".format(guild,player),'cooldown',expire = 60)

            #If Cooldown expire, Add xp and stuff
            await self.redis.sadd("{}:Level:Player".format(guild),player)

            total_xp = await self.redis.hincrby(name,"Total_XP",increment = xp)
            await self.redis.hincrby(name,"Message Count",increment = 1)

            level,remain_xp,next_xp = self.next_Level(total_xp)

            log.debug("Level:{} next xp: {} total xp:{}".format(level,next_xp,total_xp))

            lvl_db = await self.redis.hget(name,"lvl")

            if lvl_db is None:
                return await self.redis.hset(name,"lvl",1)

            elif level != int(lvl_db):
                await self.redis.hset(name, "lvl", level)
                utils.prCyan("{} - {} - {} ({}) Level up!".format(msg.guild.name,guild,msg.author,player))
                announce = await self.redis.hgetall("{}:Level:Config".format(guild))

                if announce.get("announce") == "on":
                    if announce.get("whisper") == "on":
                        await msg.author.send(announce["announce_message"].format(player = msg.author.display_name,level = level))
                    else:
                        await msg.channel.send(announce["announce_message"].format(player = msg.author.display_name,level = level))

    def next_Level(self,xp,lvl=0):
        f = 2*(lvl**2)+20*(lvl)+100
        if xp >= f:
            return self.next_Level(xp-f,lvl+1)
        return lvl,xp,f

    async def level_reward(self):
        while True:
            try:
                for guild in list(self.bot.guilds):
                    log.debug(guild)
                    if await self.redis.hget("{}:Config:Cogs".format(guild.id),"level") in (None,"off"):
                        log.debug("level reward disable")
                        continue

                    if guild.me.top_role.permissions.manage_roles: #if got Manage roles permission, can grant roles
                        log.debug("Got manage roles permissions")
                        raw_data = await self.redis.hgetall("{}:Level:role_reward".format(guild.id))
                        raw_member = await self.redis.smembers("{}:Level:Player".format(guild.id))
                        guild_roles = guild.roles
                        for member in guild.members:
                            if member.id not in raw_member:
                                continue
                            log.debug(member)
                            member_role = [x.id for x in member.roles]
                            member_level = self.next_Level(await self.redis.hget("{}:Level:Player:{}".format(guild.id,member.id),"Total_XP"))[0]
                            remove_role = []
                            add_role = []
                            for role_id, role_level in raw_data.items():
                                role_level = int(role_level)
                                if role_level == 0:
                                    continue
                                if role_id in member_role:
                                    if role_level > member_level:#if change role, and no more grant for that, remove it
                                        log.debug("role_level is bigger than member_level")
                                        remove_role.append([x for x in guild_roles if x.id == role_id][0])
                                elif role_id not in member_role:
                                    if member_level >= role_level:
                                        log.debug("role_level is less than member_level, so adding it")
                                        add_role.append([x for x in guild_roles if x.id == role_id][0])
                            if remove_role or add_role:
                                log.debug("checking if nure can add roles to member")
                                if guild.me.top_role > member.top_role:
                                    if remove_role:
                                        log.debug("removing it")
                                        await member.remove_roles(*remove_role)
                                        await asyncio.sleep(1)
                                    elif add_role:
                                        log.debug("adding it")
                                        await member.add_roles(*add_role)

            except asyncio.CancelledError:
                return utils.prRed("Asyncio Cancelled Error")
            except Exception as e:
                utils.prRed(e)
                utils.prRed(traceback.format_exc())
            self.bot.background.update({"level":datetime.datetime.now()})
            await asyncio.sleep(30)

#########################################################################
#     _____                                                       _     #
#    / ____|                                                     | |    #
#   | |        ___    _ __ ___    _ __ ___     __ _   _ __     __| |    #
#   | |       / _ \  | '_ ` _ \  | '_ ` _ \   / _` | | '_ \   / _` |    #
#   | |____  | (_) | | | | | | | | | | | | | | (_| | | | | | | (_| |    #
#    \_____|  \___/  |_| |_| |_| |_| |_| |_|  \__,_| |_| |_|  \__,_|    #
#                                                                       #
#########################################################################

    @commands.group(name="levels",aliases=["level","leaderboard"],brief="Prints a link of the guild's leaderboard",pass_context=True,invoke_without_command=True)
    async def level_link(self,ctx):
        await self.bot.say("Check this out!\nhttp://nurevam.site/level/{}".format(ctx.message.guild.id))

    @level_link.command(name="guild",brief="Prints a link of the guild leaderboard",pass_context=True)
    async def guild_level_link(self,ctx):
        await self.bot.say("Check this out!\nhttp://nurevam.site/level/guild".format(ctx.message.guild.id))

    def rank_embed(self,player,level,remain_xp,next_xp,total_exp,rank,total_rank,description=""):
        embed = discord.Embed(description=description)
        embed.set_author(name=str(player),icon_url=player.avatar_url)
        embed.add_field(name = "Level",value=str(level))
        embed.add_field(name = "EXP",value="{}/{}".format(remain_xp,next_xp))
        embed.add_field(name = "Rank",value="{}/{}".format(rank,total_rank))
        embed.add_field(name = "Total EXP",value="{}".format(total_exp))
        embed.set_footer(text=self.column[:50]) #A Cheat trick to make it one line of all field.
        if player.colour.value:
            embed.colour = player.color
        return embed

    def table_embed(self,rank_list,name_list,level_list,exp_list,total_exp,description="",page = "",guild=None):
        embed = discord.Embed(description=description)

        # adding them to field
        # Rank | Name | Level | EXP | TOTAL EXP
        new_list = []
        for x in name_list:
            new_list.append(re.sub(r"([\U00010000-\U0002FA1F])", r"\\\1",x))

        embed.add_field(name="Rank", value="**{}**".format("\n".join(rank_list)))
        embed.add_field(name="User", value="{}".format("\n".join(new_list).replace("`","")))
        embed.add_field(name="Level", value="{}".format("\n".join(level_list)))
        embed.add_field(name="EXP", value="{}".format("\n".join(exp_list)))
        embed.add_field(name="Total EXP", value="{}".format("\n".join(total_exp)))
        embed.set_footer(text=page+self.column)  # A Cheat trick to make it one line of all field.

        if guild:
            if guild.me.colour.value:
                embed.colour = guild.me.colour
        return embed

    @commands.group(brief="Prints your rank",pass_context=True,invoke_without_command=True)
    @commands.check(is_cooldown)
    async def rank(self, ctx,member:discord.Member = None):
        """
        Prints out of your rank,
        <prefix> rank
        will print out of your rank
        unless you did <prefix> rank @mention
        which will show someone's rank.
        """
        guild = ctx.message.guild.id
        player = member or ctx.message.author #if member is None, then it mean it is player self

        if await self.is_ban(player): #checking if user are banned or not
            if player.id == ctx.message.author.id: #checking if it same ID then that person is banned
                return await self.bot.say(ctx,content = "I am sorry, but you are banned. In case this is a mistake, please informate the guild owner")
            else:
                return await self.bot.say(ctx,content = "I am sorry, but {0.display_name} is banned.".format(player))

        #getting data while checking if it exists or not.
        player_data = await self.redis.hgetall("{}:Level:Player:{}".format(ctx.message.guild.id, player.id))
        if player_data is False: #checking if user are in database
            if player.id != ctx.message.author.id: #if it mention
                return await self.bot.say(ctx,content = "{} doesn't seem to be ranked yet. Tell that person to talk more!".format(player.display_name))
            else: #if it just player self
                return await self.bot.say(ctx,content = "I am sorry, but you don't seem to be ranked yet! Talk more!")

        #Getting rank places
        #it get all thing, then put them in order(which is reversed) then get player's rank positions
        data = await  self.redis.sort("{}:Level:Player".format(guild),by="{}:Level:Player:*->Total_XP".format(guild),offset = 0,count = -1)
        data = list(reversed(data))
        player_rank = data.index(str(player.id))+1
        player_data = await self.redis.hgetall("{}:Level:Player:{}".format(ctx.message.guild.id, player.id))
        level,remain_xp,next_xp = self.next_Level(int(player_data["Total_XP"]))

        #then make embed of it.
        embed = self.rank_embed(player,level,remain_xp,next_xp,player_data["Total_XP"],player_rank,len(data))

        await self.bot.say(ctx,embed=embed)

        cooldown = await self.redis.hget("{}:Level:Config".format(guild),"rank_cooldown")
        if cooldown is None or int(cooldown) == 0: #Checking guild's setting for cooldown, if not found, return. if it zero, then still return
            return
        await self.redis.set("{}:Level:{}:rank:check".format(guild, ctx.message.author.id), 'cooldown', expire=int(cooldown))

    @rank.command(name = "global",brief="Prints your global rank",pass_context=True)
    async def global_rank(self,ctx,member:discord.Member = None):
        """
        Print out global rank, meaning overall guild that share guild we were in.
        <prefix> global rank
        will print out your own rank, unless you did <prefix> global rank @mention
        which will show his/her global rank.

        Note:
            It is may not be accurate at this moment(rank positions),
        """
        player = member or ctx.message.author #if member is None, then it mean it is player self
        data = await self.redis.hgetall("Info:Level:Player_Total_XP")
        total_exp = data.get(str(player.id))
        if total_exp is None:
            return await ctx.send(content = "I am sorry, but there seem to be problem with this")

        # current_exp = await self.redis.hget("Info:Level:Player_Current_XP",player.id)

        level,remain_xp,next_xp = self.next_Level(int(total_exp))
        rank_data = sorted(data.values(),key = int,reverse = True) #getting values of dict instead then sort it and make it from highest to lowest
        rank = rank_data.index(total_exp) + 1
        embed = self.rank_embed(player,level,remain_xp,next_xp,total_exp,rank,len(rank_data),description="Global Rank")
        await self.bot.say(ctx,embed=embed)

    async def table(self,ctx,current_page,guild=None,description = ""):
        def check(reaction, user):
            if reaction.message.id == msg.id and user == player:
                if str(reaction.emoji) in [u"\u2B05", u"\u27A1"]:
                    return True
            return False
        player = ctx.message.author

        theme_setting = None
        #cache it there early, so we dont have to repeat it called when user want to go to next current_page
        #if there is guild, then it is not global
        if guild:
            log.debug("Guild requests")
            full_data = list(reversed(await self.redis.sort("{}:Level:Player".format(guild.id),
                                                 "{}:Level:Player:*->ID".format(guild.id),
                                                 "{}:Level:Player:*->Total_XP".format(guild.id),by = "{}:Level:Player:*->Total_XP".format(guild.id),offset = 0,count = -1)))
            log.debug(full_data)
            theme_setting = await self.redis.get("{}:Level:pic".format(guild.id))
            log.debug("The theme setting is {}".format(theme_setting))
        else: #global
            log.debug("Global requests")
            temp_id = await self.redis.smembers("Info:Level:Player")
            temp_total = await self.redis.hgetall("Info:Level:Player_Total_XP")
            data = sorted([(int(temp_total[x]),x) for x in temp_id],key = itemgetter(0),reverse=True)
            full_data = [main for x in data for main in x]
            log.debug(full_data)

        max_page = int(len(full_data)/30 + 1)
        log.debug("Max page is {}".format(max_page))
        if current_page >= max_page: #if it too high, it will just go to last page
            current_page = max_page

        msg = None
        embed_list = []

        for page in range(1,max_page+1):
            mpage = 1 if max_page == 1 else max_page

            rank = page * 10 - 10
            player_data = full_data[30 * (page - 1):]

            # run a loops for each of 2, in order, Total XP, ID
            rank_list = []
            name_list = []
            level_list = []
            exp_list = []
            total_list = []
            for x in range(0, len(player_data), 2):
                rank += 1
                total_exp = player_data.pop(0)
                # level, next_exp = self.next_Level(total_exp)
                level,remain_xp,next_exp = self.next_Level(int(total_exp))
                exp = "{} / {}".format(remain_xp, next_exp)

                if guild:
                    the_id = int(player_data.pop(0))
                    name = guild.get_member(int(the_id))
                    log.debug("under guild and member name is {} ||| {}".format(name,the_id))
                    if name is None: #assuming player left server and Nure didn't knew he/she have left
                        log.debug("Removing member's ID from data")
                        await self.redis.srem("{}:Level:Player".format(guild.id),the_id)
                        continue

                    else:
                        name = name.display_name
                else:
                    # the_id = player_data.pop(0)
                    name = self.bot.get_user(int(player_data.pop(0)))
                    name = name.name if name is not None else "???"

                rank_list.append(str(rank))
                name_list.append(name[:19] if theme_setting is None else name)
                level_list.append(str(level))
                exp_list.append(exp)
                total_list.append(total_exp)

                if rank == page * 10 or (len(player_data) < 30):
                    break

            if guild:
                if theme_setting:
                    log.debug("Going to make picture.")
                    data = [["Rank", "User", "Level", "EXP","Total EXP"]]
                    for x in range(len(rank_list)):
                        temp = []
                        temp.append(rank_list.pop(0))
                        temp.append(name_list.pop(0))
                        temp.append(level_list.pop(0))
                        temp.append(exp_list.pop(0))
                        temp.append(total_list.pop(0))
                        data.append(temp)

                    return await self.theme_table(ctx,data)

            #Make embed.
            embed = self.table_embed(rank_list, name_list, level_list, exp_list,total_list,description,"{}/{}".format(page,mpage))

            if guild:
                if guild.me.colour.value:
                    embed.colour = guild.me.colour
            embed_list.append(embed)

        first_start = True
        utils.prYellow(embed_list)
        while True:
            if first_start:
                first_start = False
                msg = await ctx.send(embed=embed_list[current_page-1])
                await msg.add_reaction(u"\u2B05")
                await msg.add_reaction(u"\u27A1")

            else:
                print(current_page)
                await msg.edit(embed=embed_list[current_page-1])

            try:
                react = await self.bot.wait_for("reaction_add", timeout=60, check=check)
                await msg.remove_reaction(react[0].emoji,react[1])
                await self.redis.incrby("Info:Level:Reaction_count", 1) #counting to see infos
            except asyncio.TimeoutError:
                await msg.clear_reactions()
                return

            if react[0].emoji == "⬅":
                #go back by one
                if current_page - 1 == 0: #if it on first page, don't do any
                    continue
                else:
                    current_page -= 1
            elif react[0].emoji == "➡":
                #go next page by one
                if current_page + 1 >= max_page: #if it on last page, don't do any
                    continue
                else:
                    current_page += 1


    @commands.group(name = "table",brief = "Prints the top 10 of the leaderbord",pass_context = True,invoke_without_command = True)
    async def rank_table(self, ctx,page = 1 ):
        return await self.table(ctx,page,guild = ctx.message.guild)

    @rank_table.command(name = "global",brief = "Prints the top 10 of the leaderboard global",pass_context = True)
    async def global_table(self,ctx,page = 1):
        return await self.table(ctx,page,description="Global Rank Leaderboard")

    async def theme_table(self,ctx,raw_data):
        """
        Most of this code are credit to XCang, for done most math.
        """
        img = Image.new("RGBA", (1000,1000), color=(0, 0, 0, 0))

        fnt = ImageFont.truetype('WhitneyBook.ttf', 12)
        fntb = ImageFont.truetype('WhitneySemiBold.ttf', 12)

        draw = ImageDraw.Draw(img)

        m = [0] * len(raw_data[0])
        for i, el in enumerate(raw_data):
            for j, e in enumerate(el):
                # if i == 0:
                #     wdth, hght = draw.textsize(e, font=fntb)
                #     if wdth > m[j]: m[j] = wdth
                # else:
                wdth, hght = draw.textsize(e, font=fnt)
                if wdth > m[j]: m[j] = wdth
        crop_width,crop_height = (10 + sum(m[:]) + 8 * len(m), 10 + 18 * len(raw_data) + 7)

        pic_data = await self.redis.hget("{}:Level:Config".format(ctx.message.guild.id), "pic")
        if pic_data:
            with aiohttp.ClientSession() as session:
                async with session.get(pic_data) as resp:
                    pic = Image.open(io.BytesIO(await resp.read())) #read pic and save it to memory then declare new object called im (Image)
                    aspectratio =  pic.width / pic.height
                    pic = pic.resize((crop_width,int(crop_width / aspectratio)),Image.ANTIALIAS)
                    pic = pic.crop(box = (0,int((pic.height-crop_height)/2),crop_width,int(crop_height+(pic.height-crop_height)/2)))
                    pic = pic.filter(ImageFilter.BLUR)
                    img.paste(pic)


        #adding text to picture
        """
        Runs enumerate twice as list is 2D
        It will take size of text and then return width and height
        then check if statement, for first run, which is first row (rank,user,level,exp,total exp)
        once i is not 0 anymore, It will run second statement which we can assume after first rows

        Those math are done to taken positions of putting text in

        draw.text(...)x4 for outlier then last one for overwrite and put white
        so it can be look like white text with black outlier
        """
        for i, el in enumerate(raw_data):
            for j, txt in enumerate(el):
                wdth, hght = draw.textsize(txt, font=fntb)
                font = fntb
                if i == 0:
                    if j == 0:
                        w,h = (int(10 + (m[j] - wdth) / 2), 10)
                    else:
                        w,h= (int(10 + sum(m[:j]) + (m[j] - wdth) / 2 + 8 * j), 10)
                else:
                    if j == 0:
                        w,h = (int(10 + (m[j] - wdth) / 2), 10 + 18 * i + 5)
                    else:
                        font = fnt
                        wdth, hght = draw.textsize(txt, font=fnt)
                        w,h= (int(10 + sum(m[:j]) + (m[j] - wdth) / 2 + 8 * j), 10 + 18 * i + 5)

                draw.text((w - 1, h), txt, font=font,fill="black")
                draw.text((w + 1, h), txt, font=font,fill="black")
                draw.text((w, h - 1), txt, font=font,fill="black")
                draw.text((w, h + 1), txt, font=font,fill="black")
                draw.text((w, h), txt, font=font) #White
        del draw
        #making pic crop

        img = img.crop(box=(0, 0,crop_width,crop_height))

        setting = await self.redis.hgetall("{}:Level:pic_setting".format(ctx.message.guild.id))
        utils.prCyan(setting)
        draw = ImageDraw.Draw(img)

        if setting.get("border") == "on":
            #border area
            draw.line((5, 5, 5, img.size[1] - 5), fill=(255, 255, 255, 96), width=2)
            draw.line((5, 5, img.size[0] - 5, 5), fill=(255, 255, 255, 96), width=2)
            draw.line((5, img.size[1] - 5, img.size[0] - 4, img.size[1] - 5), fill=(255, 255, 255, 96), width=2)
            draw.line((img.size[0] - 5, 5, img.size[0] - 5, img.size[1] - 5), fill=(255, 255, 255, 96), width=2)
        if setting.get("row") == "on":
            #row/column lines
            for i in range(1, len(m)):
                draw.line((int(5 + sum(m[:i]) + 8 * i), 7, int(5 + sum(m[:i]) + 8 * i), img.size[1] - 5),fill=(255, 255, 255, 48), width=1)

            for i in range(1, len(raw_data)):
                if i == 1:
                    draw.line((7, 7 + 18 * i + 2, img.size[0] - 5, 7 + 18 * i + 2), fill=(255, 255, 255, 48), width=2)
                else:
                    draw.line((7, 7 + 18 * i + 7, img.size[0] - 5, 7 + 18 * i + 7), fill=(255, 255, 255, 48), width=1)
            del draw


        fp = io.BytesIO()
        img.save(fp, format='PNG')
        fp.seek(0)
        await ctx.send(file=fp, filename="top10.png")


def setup(bot):
    bot.add_cog(Level(bot))
