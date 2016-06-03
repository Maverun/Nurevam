from discord.ext import commands
from random import randint
from .utils import utils
import asyncio
import discord
import time

from numpy import reshape as npr
import urllib.request
import re
try: import simplejson as json
except ImportError: import json

def is_enable(msg): #Checking if cogs' config for this server is off or not
    return utils.is_enable(msg, "level")

def is_cooldown(msg):
    redis = utils.redis
    config = redis.get("{}:Level:{}:rank:check".format(msg.message.server.id,msg.message.author.id))
    if config is None:
        return True
    else:
        return False

class Level():
    def __init__(self,bot):
        self.bot = bot
        self.redis = bot.db.redis
        self.bot.say_edit = bot.says_edit

    async def is_ban(self,msg):
        is_ban_member = await self.redis.smembers("{}:Level:banned_members".format(msg.server.id))
        is_ban_role = await self.redis.smembers("{}:Level:banned_roles".format(msg.server.id))
        for role in msg.author.roles:
            if role.id in is_ban_role:
                return True
        if msg.author.id in is_ban_member:
            return True
        return False

    async def on_message(self,msg): #waiting for player reply
        if msg.author == self.bot.user:
            return
        if msg.channel.is_private:
            return
        if await self.is_ban(msg) is True:
            return
        if await self.redis.hget("{}:Config:Cogs".format(msg.server.id),"level") == "off":
            return
        elif await self.redis.hget("{}:Config:Cogs".format(msg.server.id),"level") == "on":
            #Getting ID
            player = msg.author.id
            server = msg.server.id
            await self.redis.set('{}:Level:Server_Name'.format(server),msg.server.name)
            if msg.server.icon:
                await self.redis.set('{}:Level:Server_Icon'.format(server),msg.server.icon)
            self.name = "{}:Level:Player:{}".format(server,player)
            list = await self.redis.exists(self.name) #Call of name and ID to get boolean
            if list is False: # if it False, then it will update a new list for player who wasnt in level record
                await self.new_profile(msg)
            await self.redis.hincrby(self.name,"Total Message Count",increment=1)
            await self.redis.hset(self.name,"ID",player)
            await self.redis.hset(self.name,"Name",msg.author.name)
            check = await self.redis.get("{}:Level:{}:xp:check".format(server,player))
            if check: #If it true, return, it haven't cool down yet
                return
            #If Cooldown expire, Add xp and stuff
            await self.redis.sadd("{}:Level:Player".format(server),player)
            await self.redis.hset(self.name,"Discriminator",msg.author.discriminator)
            if msg.author.avatar:
                await self.redis.hset(self.name,"Avatar",msg.author.avatar)
            xp = randint(5,10)
            await self.redis.hincrby(self.name,"XP",increment=(xp))
            await self.redis.hincrby(self.name,"Total_XP",increment=(xp))
            await self.redis.hincrby(self.name,"Message Count",increment=1)
            current_xp=await self.redis.hget(self.name,"XP")
            Next_XP=await self.redis.hget(self.name,"Next_XP")
            if int(current_xp) >= int(Next_XP):
                level = await self.redis.hget(self.name,"Level")
                traits_check =await self.redis.hget("{}:Level:Trait".format(server),"{}".format(level))
                if traits_check is not None:
                    traits = traits_check
                else:
                    traits = randint(1,3)
                Remain_XP = int(current_xp) - int(Next_XP)
                await self.next_Level(Remain_XP)
                await self.redis.hset("{}:Level:Trait".format(server),level,traits)
                await self.redis.hincrby(self.name,"Total_Traits_Points",increment=traits)
                utils.prCyan("{} - {} - {} ({}) Level up!".format(msg.server.id,server,msg.author,player))
                announce = await self.redis.hgetall("{}:Level:Config".format(server))
                if announce.get("announce",False) == "on":
                    print("whisper")
                    if announce.get("whisper",False) == "on":
                        await self.bot.send_message(msg.author,announce["announce_message"].format(player=msg.author.name,level=int(level)+1))
                    else:
                        await self.bot.send_message(msg.channel,announce["announce_message"].format(player=msg.author.name,level=int(level)+1))
            await self.redis.set("{}:Level:{}:xp:check".format(server,player),'cooldown',expire=60)

    async def new_profile(self, msg): #New Profile
        await self.redis.hmset(self.name,
                         "Name",str(msg.author),
                          "ID",str(msg.author.id),
                          "Level",1,
                          "XP",0,
                          "Next_XP",100,
                          "Total_XP",0,
                          "Message Count",0,
                          "Total_Traits_Points",0)


    async def next_Level(self, xp):
        level = await self.redis.hget(self.name,"Level")
        new_xp = int(100 * (1.2 ** int(level)))
        await self.redis.hset(self.name,"Next_XP", (new_xp))
        await self.redis.hset(self.name,"XP",xp)
        await self.redis.hincrby(self.name,"Level",increment=1)


#########################################################################
#     _____                                                       _     #
#    / ____|                                                     | |    #
#   | |        ___    _ __ ___    _ __ ___     __ _   _ __     __| |    #
#   | |       / _ \  | '_ ` _ \  | '_ ` _ \   / _` | | '_ \   / _` |    #
#   | |____  | (_) | | | | | | | | | | | | | | (_| | | | | | | (_| |    #
#    \_____|  \___/  |_| |_| |_| |_| |_| |_|  \__,_| |_| |_|  \__,_|    #
#                                                                       #
#########################################################################

    @commands.group(name="levels",aliases=["level","leaderboard"],brief="Show a link of server's leaderboard",pass_context=True,invoke_without_command=True)
    @commands.check(is_enable)
    async def level_link(self,msg):
        await self.bot.say("Check this out!\nhttp://nurevam.site/levels/{}".format(msg.message.server.id))

    @level_link.command(name="server",brief="Show a link of all server's leaderboard",pass_context=True)
    @commands.check(is_enable)
    async def server_level_link(self,msg):
        await self.bot.say("Check this out!\nhttp://nurevam.site/server/levels".format(msg.message.server.id))

    @commands.command(name="rank",brief="Allow to see what rank you are at",pass_context=True)
    @commands.check(is_enable)
    @commands.check(is_cooldown)
    async def rank(self,msg):
        server = msg.message.server.id
        if msg.message.mentions != []:
            player = msg.message.mentions[0]
        else:
            player = msg.message.author
        if await self.is_ban(msg.message) is True:
            await self.bot.say_edit("I am sorry, but you are banned, if you think this is wrong, please info server owner")
            return
        if await self.redis.exists("{}:Level:Player:{}".format(msg.message.server.id,player.id)) is False:
            if player != msg.message.author:
                await self.bot.say_edit("{} seem to be not a ranked yet, Tell that person to talk more!".format(player.mention))
                return
            else:
                await self.bot.say_edit("I am sorry, it seem you are not in a rank list! Talk more!")
                return
        data = await  self.redis.sort("{}:Level:Player".format(server),by="{}:Level:Player:*->Total_XP".format(server),offset=0,count=-1)
        data = list(reversed(data))
        player_rank = data.index(player.id)+1
        player_data = await self.redis.hgetall("{}:Level:Player:{}".format(msg.message.server.id,player.id))
        # await self.bot.say_edit("```xl\n{}: Level: {} | EXP: {}/{} | Total XP: {} | Rank: {}/{} | Traits: {}\n```".format(player.name.lower(),player_data["Level"],
        #                                                                                                              player_data["XP"],player_data["Next_XP"],
        #                                                                                                              player_data["Total_XP"],player_rank,len(data),player_data["Total_Traits_Points"]))
        await self.bot.say_edit("```xl\n{}: Level: {} | EXP: {}/{} | Total XP: {} | Rank: {}/{}\n```".format(player.name.lower(),player_data["Level"],
                                                                                                                     player_data["XP"],player_data["Next_XP"],
                                                                                                                     player_data["Total_XP"],player_rank,len(data)))
        cooldown = await self.redis.hget("{}:Level:Config".format(server),"rank_cooldown")
        if cooldown is None:
            return
        if int(cooldown) == 0:
            return
        await self.redis.set("{}:Level:{}:rank:check".format(server,msg.message.author.id),'cooldown',expire=int(cooldown))



    @commands.command(name="table",brief="Allow to see top 10 rank",pass_context=True)
    @commands.check(is_enable)
    async def rank_table(self,msg):
        server = msg.message.server.id
        player_data = await  self.redis.sort("{}:Level:Player".format(server),"{}:Level:Player:*->Name".format(server),
                                                                             "{}:Level:Player:*->Level".format(server),
                                                                             "{}:Level:Player:*->XP".format(server),
                                                                             "{}:Level:Player:*->Next_XP".format(server),
                                                                             "{}:Level:Player:*->Total_XP".format(server),
                                                                             by="{}:Level:Player:*->Total_XP".format(server),offset=0,count=-1)
        struct_player_data = npr(player_data, (-1, 5))
        struct_player_data = struct_player_data[-10:]
        del player_data[:]
        to_print = []

        def column(matrix, i):
            return [row[i] for row in matrix]

        ###storage https://discordapp.com/assets/72635fda0f6d2188e224.js
        ##local file (2 lines):
        #with open('repchars.json', 'r', encoding="utf8") as rep_file:
        #    rep = json.load(rep_file)

        ##web file (38 lines):
        hdr = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
            'Accept-Encoding': 'none',
            'Accept-Language': 'en-US,en;q=0.8',
            'Connection': 'keep-alive'}
        req = urllib.request.Request("https://discordapp.com/assets/72635fda0f6d2188e224.js", headers=hdr)
        f = urllib.request.urlopen(req)
        rep = f.read().decode('utf-8')
        s = rep.split('\n')
        rep = '{}{}'.format(s[51], s[52])
        del s

        repi = rep.find(u"function(e,t){e.exports={")
        if repi == -1:
            return await self.bot.say_edit("Can\'t find pattern start in file.")
        rep = rep[repi+24:] #24 is length of find string to "{"
        
        repi = rep.find(u"}},function(e,t){e.exports=[{")
        if repi == -1:
            return await self.bot.say_edit("Can\'t find pattern exit in file.")
        rep = rep[:repi+1] # 1 to } in }}

        rep = re.sub(r"\w+\:\[", u"", rep)                  #1 del word:[
        rep = re.sub(r"[\[\]]", u"", rep)                   #2 del []
        rep = re.sub(r"\},\{", u",", rep)                   #3 rep },{ to ,
        rep = re.sub(r",surrogates", u"", rep)              #4 del ,surrogates
        rep = re.sub(r"\{+", u"{", rep)                     #5 rep {{ to {
        rep = re.sub(r"\}+", u"}", rep)                     #6 rep }} to }
        rep = re.sub(r"hasDiversity:!0,", u"", rep)         #7 del hasDiversity:!0,
        rep = re.sub(r"\"[^ℹ]\w+\",", u"", rep)             #8 del multiple smile condition
        rep = re.sub(r"(\")(\w{3,})(\")", r"\1:\2:\3", rep) #9 rep "smile" to ":smile:"

        rep = json.loads(rep)
        ret = {}
        for k in rep:
            ret[rep[k]] = k
        rep = ret
        del ret
        #end web reading

        lenname = [0] * len(struct_player_data)
        lenu = [0] * len(struct_player_data)
        ml = 0
        rep = dict((re.escape(k), v) for k, v in rep.items())
        pattern = re.compile("|".join(rep.keys()))
        for row in range(0, len(struct_player_data)):
            struct_player_data[row][0] = pattern.sub(lambda m: rep[re.escape(m.group(0))], struct_player_data[row][0])

            lenname[row] = [m.end(0) - m.start(0) for m in re.finditer(u'[\u0300-\u036f\uff9f]+', struct_player_data[row][0])]
            if lenname[row] == []:
                if len(struct_player_data[row][0]) > ml:
                    ml = len(struct_player_data[row][0])
                lenname[row] = 0
            else:
                if len(struct_player_data[row][0])-sum(lenname[row]) > ml:
                    ml = len(struct_player_data[row][0]) - sum(lenname[row])
                lenname[row] = len(struct_player_data[row][0]) - sum(lenname[row])

            lenu[row] = [m.end(0) - m.start(0) for m in re.finditer(u'[\u0530-\uffff\U00010000-\U0001F9FF]+', struct_player_data[row][0])]
            if lenu[row] == []:
                lenu[row] = 0
            else:
                lenu[row] = sum(lenu[row])
                if lenu[row]%3 == 1:
                    lenu[row] -= 1
                elif lenu[row]%3 == 2:
                    lenu[row] -= 2

        for row in range(0, len(struct_player_data)):
            if lenname[row] == 0: 
                lenname[row] = ml
            else:
                if len(struct_player_data[row][0]) < ml:
                    lenname[row] = ml - len(struct_player_data[row][0]) + lenname[row]

            to_print.append("║{:0>{index}d}│{:<{name}s}{:>{name2}s} │ Level: {:>{level}} │ EXP: {:>{first}} / {:<{second}} │ Total XP: {:>{total}} ║\n".format(
                len(struct_player_data)-row, struct_player_data[row][0], '',
                struct_player_data[row][1], struct_player_data[row][2], struct_player_data[row][3], struct_player_data[row][4],
                index=len(str(len(struct_player_data))),
                name=ml, name2=ml - lenname[row] + int(round((int(max(lenu)) - lenu[row]) / 2.5)),
                level=len(str(max(list(map(int,column(struct_player_data, 1)))))),
                first=len(str(max(list(map(int,column(struct_player_data, 2)))))),
                second=len(str(max(list(map(int,column(struct_player_data, 3)))))),
                total=len(str(max(list(map(int,column(struct_player_data, 4))))))))
        #extra borders
        to_print.append("╔{0:═>{index}}╤{0:═>{name_m}}═╤════════{0:═>{level}}═╤══════{0:═>{first}}═══{0:═>{second}}═╤═══════════{0:═>{total}}═╗\n".format(
            '', index=len(str(len(struct_player_data))),
            name_m=ml + int(round((int(max(lenu)) - int(min(lenu))) / 2.5)),
            level=len(str(max(list(map(int,column(struct_player_data, 1)))))),
            first=len(str(max(list(map(int,column(struct_player_data, 2)))))),
            second=len(str(max(list(map(int,column(struct_player_data, 3)))))),
            total=len(str(max(list(map(int,column(struct_player_data, 4))))))))
        to_print.insert(0, "╚{0:═>{index}}╧{0:═>{name_m}}═╧════════{0:═>{level}}═╧══════{0:═>{first}}═══{0:═>{second}}═╧═══════════{0:═>{total}}═╝\n".format(
            '', index=len(str(len(struct_player_data))),
            name_m=ml + int(round((int(max(lenu)) - int(min(lenu))) / 2.5)),
            level=len(str(max(list(map(int,column(struct_player_data, 1)))))),
            first=len(str(max(list(map(int,column(struct_player_data, 2)))))),
            second=len(str(max(list(map(int,column(struct_player_data, 3)))))),
            total=len(str(max(list(map(int,column(struct_player_data, 4))))))))
        """ single border
        to_print.append("┌{0:─>{index}}┬{0:─>{name_m}}─┬────────{0:─>{level}}─┬──────{0:─>{first}}───{0:─>{second}}─┬───────────{0:─>{total}}─┐\n".format(
            '', index=len(str(len(struct_player_data))),
            name_m=ml + int(round((int(max(lenu)) - int(min(lenu))) / 2.5)),
            level=len(str(max(list(map(int,column(struct_player_data, 1)))))),
            first=len(str(max(list(map(int,column(struct_player_data, 2)))))),
            second=len(str(max(list(map(int,column(struct_player_data, 3)))))),
            total=len(str(max(list(map(int,column(struct_player_data, 4))))))))
        to_print.insert(0, "└{0:─>{index}}┴{0:─>{name_m}}─┴────────{0:─>{level}}─┴──────{0:─>{first}}───{0:─>{second}}─┴───────────{0:─>{total}}─┘\n".format(
            '', index=len(str(len(struct_player_data))),
            name_m=ml + int(round((int(max(lenu)) - int(min(lenu))) / 2.5)),
            level=len(str(max(list(map(int,column(struct_player_data, 1)))))),
            first=len(str(max(list(map(int,column(struct_player_data, 2)))))),
            second=len(str(max(list(map(int,column(struct_player_data, 3)))))),
            total=len(str(max(list(map(int,column(struct_player_data, 4))))))))"""
        await self.bot.say_edit("```xl\n{}\n```".format("".join(reversed(to_print))))


def setup(bot):
    bot.add_cog(Level(bot))
