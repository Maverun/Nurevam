from discord.ext import commands
from operator import itemgetter
from random import randint
from .utils import utils
import discord
import math

def is_cooldown(msg):
    redis = utils.redis
    config = redis.get("{}:Level:{}:rank:check".format(msg.message.server.id,msg.message.author.id))
    return not(bool(config))

def is_enable(ctx): #Checking if cogs' config for this server is off or not
    return utils.is_enable(ctx, "level")

class Level:
    """
    A level plugins, gain exp when talking.
    """
    def __init__(self,bot):
        self.bot = bot
        self.redis = bot.db.redis
        self.bot.say_edit = bot.says_edit
        self.column = utils.secret["column"] #U mad bro?

#Those will set expire when member leave server, to get new "space", they have 2 weeks to return, other wise, level data of their will be lost.
    async def on_member_remove(self,member):
        await self.redis.srem("{}:Level:Player".format(member.server.id),member.id)
        await self.redis.expire("{}:Level:Player:{}".format(member.server.id,member.id),1209600)#setting expire dated for member, will last for 2 weeks, if there is change, it will stop expire, aka talk in server

    async def on_member_join(self,member):
        if await self.redis.exists("{}:Level:Player:{}".format(member.server.id,member.id)):
            await self.redis.persist("{}:Level:Player:{}".format(member.server.id,member.id))

    async def on_member_update(self,before,after):
        if before.display_name != after.display_name:
            await self.redis.hset("{}:Level:Player:{}".format(after.server.id,after.id),"Name",after.display_name)

    async def is_ban(self,member):
        if isinstance(member,discord.Member):
            is_ban_member = await self.redis.smembers("{}:Level:banned_members".format(member.server.id))
            is_ban_role = await self.redis.smembers("{}:Level:banned_roles".format(member.server.id))
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
        total_xp = await self.redis.hincrby("Info:Level:Player_Total_XP",msg.author.id,increment = xp)
        current_xp = await self.redis.hincrby("Info:Level:Player_Current_XP",msg.author.id,increment = xp)
        next_xp = await self.redis.hget("Info:Level:Player_Next_XP",msg.author.id)
        if next_xp is None:
            next_xp = 100
        else:
            next_xp = int(next_xp)

        if current_xp >= next_xp:
            remain_xp = current_xp - next_xp
            level, new_xp = self.next_Level(total_xp)
            await self.redis.hset("Info:Level:Player_Current_XP",msg.author.id,remain_xp)
            await self.redis.hset("Info:Level:Player_Next_XP",msg.author.id,new_xp)
            utils.prCyan("Global Level- {} ({}) Level up!".format(msg.author, msg.author.id))
        return

    async def on_message(self,msg): #waiting for player reply
        if msg.author == self.bot.user or msg.channel.is_private:
            return
        if int(msg.author.discriminator) == 0000:
            return #Webhook
        if await self.redis.hget("{}:Config:Cogs".format(msg.server.id),"level") == "on":
            xp = randint(5,10)
            await self.on_message_global(msg,xp)
            if await self.is_ban(msg.author) is True:
                return
            #Getting ID
            player = msg.author.id
            server = msg.server.id
            self.name = "{}:Level:Player:{}".format(server,player) #future references for easier to use
            check_exist = await self.redis.exists(self.name) #Call of name and ID to get boolean
            if check_exist is False: # if it False, then it will update a new list for player who wasn't in level record
                await self.new_profile(msg)
            await self.redis.hincrby(self.name,"Total Message Count",increment = 1)
            if await self.redis.get("{}:Level:{}:xp:check".format(server,player)):#If it true, return, it haven't cool down yet
                return
            #Setting cooldown, in case something happen, it wont increase xp twice while it still affect some reason, such as data slow.
            await self.redis.set("{}:Level:{}:xp:check".format(server,player),'cooldown',expire = 60)
            #If Cooldown expire, Add xp and stuff
            await self.redis.sadd("{}:Level:Player".format(server),player)
            current_xp = await self.redis.hincrby(self.name,"XP",increment = xp)
            total_xp = await self.redis.hincrby(self.name,"Total_XP",increment = xp)
            await self.redis.hincrby(self.name,"Message Count",increment = 1)
            next_xp = await self.redis.hget(self.name,"Next_XP")
            if next_xp == None: #Some reason i get error that Next XP is missing, so best to this way to stop giving error while setting it
                return await self.redis.hset(self.name,"Next_XP",100)
            next_xp = int(next_xp)
            if current_xp >= next_xp:
                remain_xp = current_xp - next_xp
                level,new_xp = self.next_Level(total_xp)
                await self.redis.hmset(self.name, "Next_XP", new_xp, "XP", remain_xp)  # puting them in database
                utils.prCyan("{} - {} - {} ({}) Level up!".format(msg.server.name,server,msg.author,player))
                announce = await self.redis.hgetall("{}:Level:Config".format(server))
                if announce.get("announce") == "on":
                    print("whisper")
                    if announce.get("whisper") == "on":
                        await self.bot.send_message(msg.author,announce["announce_message"].format(player = msg.author.display_name,level = level))
                    else:
                        await self.bot.send_message(msg.channel,announce["announce_message"].format(player = msg.author.display_name,level = level))

    async def new_profile(self, msg): #New Profile
        await self.redis.hmset(self.name,
                          "ID",msg.author.id,
                          "XP",0,
                          "Next_XP",100,
                          "Total_XP",0,
                          "Message Count",0,
                          "Total_Traits_Points",0)


    def next_Level(self,total):
        """
        Formula to get next xp is 100*1.2^level
        It will do calculate level by using log
        then use that level to sub first equations for next level
        This to ensure to make it accurate as it could.
        """
        if int(total) >= 100: #if it greater than 100, it mean it above level 1
            level = int(math.log(int(total)/100,1.2)) #getting level
        else: #when total exp is less than 100, it is still level 1, reason for that is due to -level via log equations
            level = 1
        next_xp = int(100 * (1.2 ** level)) #getting next require
        return level,next_xp

#########################################################################
#     _____                                                       _     #
#    / ____|                                                     | |    #
#   | |        ___    _ __ ___    _ __ ___     __ _   _ __     __| |    #
#   | |       / _ \  | '_ ` _ \  | '_ ` _ \   / _` | | '_ \   / _` |    #
#   | |____  | (_) | | | | | | | | | | | | | | (_| | | | | | | (_| |    #
#    \_____|  \___/  |_| |_| |_| |_| |_| |_|  \__,_| |_| |_|  \__,_|    #
#                                                                       #
#########################################################################

    @commands.group(name="levels",aliases=["level","leaderboard"],brief="Prints a link of the server's leaderboard",pass_context=True,invoke_without_command=True)
    @commands.check(is_enable)
    async def level_link(self,ctx):
        await self.bot.says_edit("Check this out!\nhttp://nurevam.site/levels/{}".format(ctx.message.server.id))

    @level_link.command(name="server",brief="Prints a link of the server leaderboard",pass_context=True)
    @commands.check(is_enable)
    async def server_level_link(self,ctx):
        await self.bot.says_edit("Check this out!\nhttp://nurevam.site/server/levels".format(ctx.message.server.id))

    def rank_embed(self,player,level,current_exp,next_xp,total_exp,rank,total_rank,description=""):
        embed = discord.Embed(description=description)
        embed.set_author(name=str(player),icon_url=player.avatar_url)
        embed.add_field(name = "Level",value=str(level))
        embed.add_field(name = "EXP",value="{}/{}".format(current_exp,next_xp))
        embed.add_field(name = "Total XP",value=total_exp)
        embed.add_field(name = "Rank",value="{}/{}".format(rank,total_rank))
        embed.set_footer(text=self.column[:50]) #A Cheat trick to make it one line of all field.
        if player.colour.value:
            embed.colour = player.color
        return embed

    def table_embed(self,rank_list,name_list,level_list,exp_list,total_list,description="",server=None):
        embed = discord.Embed(description=description)

        # adding them to field
        # Rank | Name | Level | EXP | TOTAL EXP
        embed.add_field(name="Rank", value="`{}`".format("\n".join(rank_list)))
        embed.add_field(name="User", value="`{}`".format("\n".join(name_list).replace("`","")))
        embed.add_field(name="Level", value="`{}`".format("\n".join(level_list)))
        embed.add_field(name="EXP", value="`{}`".format("\n".join(exp_list)))
        embed.add_field(name="Total EXP", value="`{}`".format("\n".join(total_list)))
        embed.set_footer(text=self.column)  # A Cheat trick to make it one line of all field.
        if server:
            if server.me.colour.value:
                embed.colour = server.me.colour
        return embed

    @commands.group(brief="Prints your rank",pass_context=True,invoke_without_command=True)
    @commands.check(is_enable)
    @commands.check(is_cooldown)
    async def rank(self, ctx,member:discord.Member = None):
        """
        Prints out of your rank,
        <prefix> rank
        will print out of your rank
        unless you did <prefix> rank @mention
        which will show someone's rank.
        """
        server = ctx.message.server.id
        player = member or ctx.message.author #if member is None, then it mean it is player self
        if await self.is_ban(player): #checking if user are banned or not
            if player.id == ctx.message.author.id: #checking if it same ID then that person is banned
                return await self.bot.say_edit("I am sorry, but you are banned. In case this is a mistake, please informate the server owner")
            else:
                return await self.bot.says_edit("I am sorry, but {0.display_name} is banned.".format(player))
        #getting data while checking if it exists or not.
        player_data = await self.redis.hgetall("{}:Level:Player:{}".format(ctx.message.server.id, player.id))
        if player_data is False: #checking if user are in database
            if player.id != ctx.message.author.id: #if it mention
                return await self.bot.say_edit("{} doesn't seem to be ranked yet. Tell that person to talk more!".format(player.display_name))
            else: #if it just player self
                return await self.bot.say_edit("I am sorry, but you don't seem to be ranked yet! Talk more!")
        #Getting rank places
        #it get all thing, then put them in order(which is reversed) then get player's rank positions
        data = await  self.redis.sort("{}:Level:Player".format(server),by="{}:Level:Player:*->Total_XP".format(server),offset = 0,count = -1)
        data = list(reversed(data))
        player_rank = data.index(player.id)+1
        player_data = await self.redis.hgetall("{}:Level:Player:{}".format(ctx.message.server.id, player.id))
        level,next_xp = self.next_Level(player_data["Total_XP"])
        #then make embed of it.
        embed = self.rank_embed(player,level,player_data["XP"],next_xp,player_data["Total_XP"],player_rank,len(data))
        await self.bot.says_edit(embed=embed)
        cooldown = await self.redis.hget("{}:Level:Config".format(server),"rank_cooldown")
        if cooldown is None: #Checking server's setting for cooldown, if not found, return. if it zero, then still return
            return
        elif int(cooldown) == 0:
            return
        await self.redis.set("{}:Level:{}:rank:check".format(server, ctx.message.author.id), 'cooldown', expire=int(cooldown))

    @rank.command(name = "global",brief="Prints your global rank",pass_context=True)
    @commands.check(is_enable)
    async def global_rank(self,ctx,member:discord.Member = None):
        """
        Print out global rank, meaning overall server that share server we were in.
        <prefix> global rank
        will print out your own rank, unless you did <prefix> global rank @mention
        which will show his/her global rank.

        Note:
            It is may not be accurate at this moment(rank positions),
        """
        player = member or ctx.message.author #if member is None, then it mean it is player self
        data = await self.redis.hgetall("Info:Level:Player_Total_XP")
        total_exp = data[player.id]
        current_exp = await self.redis.hget("Info:Level:Player_Current_XP",player.id)
        level, next_xp = self.next_Level(total_exp)
        rank_data = sorted(data.values(),key = int,reverse = True) #getting values of dict instead then sort it and make it from highest to lowest
        rank = rank_data.index(total_exp) + 1
        embed = self.rank_embed(player,level,current_exp,next_xp,total_exp,rank,len(rank_data),description="Global Rank")
        await self.bot.says_edit(embed=embed)

    async def table(self, user, current_page,server=None,description = ""):
        #cache it there early, so we dont have to repeat it called when user want to go to next current_page
        #if there is server, then it is not global
        if server:
            full_data = list(reversed(await self.redis.sort("{}:Level:Player".format(server.id),
                                                 "{}:Level:Player:*->ID".format(server.id),
                                                 "{}:Level:Player:*->XP".format(server.id),
                                                 "{}:Level:Player:*->Total_XP".format(server.id),by = "{}:Level:Player:*->Total_XP".format(server.id),offset = 0,count = -1)))
        else: #global
            temp_id = await self.redis.smembers("Info:Level:Player")
            temp_current = await self.redis.hgetall("Info:Level:Player_Current_XP")
            temp_total = await self.redis.hgetall("Info:Level:Player_Total_XP")
            name_data = await self.redis.hgetall("Info:Name")
            data = sorted([(int(temp_total[x]),temp_current[x],x) for x in temp_id],key = itemgetter(0),reverse=True)
            full_data = [main for x in data for main in x]
        max_page = int(len(full_data)/30 + 1)
        if current_page >= max_page: #if it too high, it will just go to last page
            current_page = max_page
        first_start = True
        msg = None
        while True:
            rank = current_page * 10 - 10
            player_data = full_data[30 * (current_page - 1):]
            # run a loops for each of 3, in order, Total XP , XP , ID
            rank_list = []
            name_list = []
            level_list = []
            exp_list = []
            total_list = []
            for x in range(0, len(player_data), 3):
                rank += 1
                # utils.prYellow(player_data[x])
                # utils.prYellow(player_data[x + 2])
                total_exp =player_data.pop(0)
                level, next_exp = self.next_Level(total_exp )
                exp = "{} / {}".format(player_data.pop(0), next_exp)
                if server:
                    name = server.get_member(player_data.pop(0))
                    if name is None:
                        continue
                    else:
                        name = name.display_name
                else:
                    name = name_data.get(player_data.pop(0),"???")
                rank_list.append(str(rank))
                name_list.append(name[:19])
                level_list.append(str(level))
                exp_list.append(exp)
                total_list.append(str(total_exp))
                if rank == current_page * 10 or (len(player_data) < 30):
                    break
            #Make embed.
            embed = self.table_embed(rank_list, name_list, level_list, exp_list, total_list,description)
            if server:
                if server.me.colour.value:
                    embed.colour = server.me.colour
            if first_start:
                first_start = False
                msg = await self.bot.say(embed=embed)
                await self.bot.add_reaction(msg,u"\u2B05")
                await self.bot.add_reaction(msg,u"\u27A1")
            else:
                msg = await self.bot.edit_message(msg,embed=embed)
            react = await self.bot.wait_for_reaction([u"\u2B05",u"\u27A1"],message=msg,user=user,timeout=120)
            if react is None:
               return
            await self.bot.remove_reaction(msg,react.reaction.emoji,user)
            if react.reaction.emoji == "⬅":
                #go back by one
                if current_page - 1 == 0: #if it on first page, dont do any
                    continue
                else:
                    current_page -= 1
            elif react.reaction.emoji == "➡":
                #go next page by one
                if current_page + 1 == max_page: #if it on last page, dont do any
                    continue
                else:
                    current_page += 1


    @commands.group(name = "table",brief = "Prints the top 10 of the leaderbord",pass_context = True,invoke_without_command = True)
    @commands.check(is_enable)
    async def rank_table(self, ctx,page = 1 ):
        return await self.table(ctx.message.author,page,server = ctx.message.server)

    @rank_table.command(name = "global",brief = "Prints the top 10 of the leaderboard global",pass_context = True)
    @commands.check(is_enable)
    async def global_table(self,ctx,page = 1):
        return await self.table(ctx.message.author,page,description="Global Rank Leaderboard")

    @commands.command(hidden = True)
    @commands.check(is_enable)
    async def temp_global(self):
        print("Temp_global")
        data_level = []
        for x in list(self.bot.servers):
            data_level += await self.redis.smembers("{}:Level:Player".format(x.id))
        await self.redis.delete("Info:Level:Player") # refresh level plugin player, in case that player left server or changed
        await self.redis.sadd("Info:Level:Player",*data_level) #add member ID to database
        data_member_total_exp = {}
        data_member_current_exp = {}
        data_member_next_xp = {}
        print("checking loops")
        for x in data_level:
            total_exp = 0
            current_exp = 0
            async for key in self.redis.iscan(match="*Level:Player:{}".format(x)): #getting key relative to that player
                if await self.redis.hget(key,"Total_XP"):
                    total_exp += int(await self.redis.hget(key,"Total_XP"))
                if await self.redis.hget(key,"XP"):
                    current_exp += int(await self.redis.hget(key,"XP"))
            level,new_xp = self.next_Level(total_exp)
            data_member_total_exp[x] = total_exp
            data_member_current_exp[x] = current_exp
            data_member_next_xp[x] = new_xp
        utils.prCyan("Done updating level")
        await self.redis.hmset_dict("Info:Level:Player_Total_XP",data_member_total_exp)
        await self.redis.hmset_dict("Info:Level:Player_Current_XP",data_member_current_exp)
        await self.redis.hmset_dict("Info:Level:Player_Next_XP",data_member_current_exp)


def setup(bot):
    bot.add_cog(Level(bot))
