from prettytable import PrettyTable
from discord.ext import commands
from random import randint
from .utils import utils
import discord
import math

def is_cooldown(msg):
    redis = utils.redis
    config = redis.get("{}:Level:{}:rank:check".format(msg.message.server.id,msg.message.author.id))
    return bool(config)

class Level():
    def __init__(self,bot):
        self.bot = bot
        self.redis = bot.db.redis
        self.bot.say_edit = bot.says_edit

    async def on_member_remove(self,member):
        await self.redis.srem("{}:Level:Player".format(member.server.id),member.id)

    async def on_member_update(self,before,after):
        if before.display_name != after.display_name:
            await self.redis.hset("{}:Level:Player:{}".format(after.server.id,after.id),"Name",after.display_name)

    async def is_ban(self,msg):
        is_ban_member = await self.redis.smembers("{}:Level:banned_members".format(msg.server.id))
        is_ban_role = await self.redis.smembers("{}:Level:banned_roles".format(msg.server.id))
        try: #Need to debug this later on.
            for role in msg.author.roles:
                if role.id in is_ban_role:
                    return True
        except:
            if msg.channel.is_private:
                utils.prRed("It is under private")
            else:
                utils.prRed("name: {0.name}, id:{0.id}, person: {1}, {1.id}".format(msg.server,msg.author))
        if msg.author.id in is_ban_member:
            return True
        return False

    async def on_message(self,msg): #waiting for player reply
        if msg.author == self.bot.user or msg.channel.is_private:
            return
        if int(msg.author.discriminator) == 0000:
            return #Webhook
        if await self.is_ban(msg) is True:
            return
        if await self.redis.hget("{}:Config:Cogs".format(msg.server.id),"level") == "on":
            #Getting ID
            player = msg.author.id
            server = msg.server.id
            self.name = "{}:Level:Player:{}".format(server,player)
            check_exist = await self.redis.exists(self.name) #Call of name and ID to get boolean
            if check_exist is False: # if it False, then it will update a new list for player who wasnt in level record
                await self.new_profile(msg)
            await self.redis.hincrby(self.name,"Total Message Count",increment=1)
            await self.redis.hset(self.name,"ID",player)
            await self.redis.hset(self.name,"Name",msg.author.name)
            if await self.redis.get("{}:Level:{}:xp:check".format(server,player)):#If it true, return, it haven't cool down yet
                return
            #If Cooldown expire, Add xp and stuff
            await self.redis.sadd("{}:Level:Player".format(server),player)
            await self.redis.hset(self.name,"Discriminator",msg.author.discriminator)
            xp = randint(5,10)
            current_xp = await self.redis.hincrby(self.name,"XP",increment=(xp))
            await self.redis.hincrby(self.name,"Total_XP",increment=(xp))
            await self.redis.hincrby(self.name,"Message Count",increment=1)
            Next_XP=await self.redis.hget(self.name,"Next_XP")
            if Next_XP == None: #Some reason i get error that Next XP is missing, so best to this way to stop giving error while setting it
                await self.redis.hset(self.name,"Next_XP",100)
                return
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
                utils.prCyan("{} - {} - {} ({}) Level up!".format(msg.server.name,server,msg.author,player))
                announce = await self.redis.hgetall("{}:Level:Config".format(server))
                if announce.get("announce") == "on":
                    print("whisper")
                    if announce.get("whisper") == "on":
                        await self.bot.send_message(msg.author,announce["announce_message"].format(player=msg.author.display_name,level=int(level)+1))
                    else:
                        await self.bot.send_message(msg.channel,announce["announce_message"].format(player=msg.author.display_name,level=int(level)+1))
            await self.redis.set("{}:Level:{}:xp:check".format(server,player),'cooldown',expire=60)

    async def new_profile(self, msg): #New Profile
        await self.redis.hmset(self.name,
                         "Name",msg.author.display_name,
                          "ID",str(msg.author.id),
                          "Level",1,
                          "XP",0,
                          "Next_XP",100,
                          "Total_XP",0,
                          "Message Count",0,
                          "Total_Traits_Points",0)


    async def next_Level(self, xp):
        level = await self.redis.hget(self.name,"Level") or 1
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
    async def level_link(self,msg):
        await self.bot.says_edit("Check this out!\nhttp://nurevam.site/levels/{}".format(msg.message.server.id))

    @level_link.command(name="server",brief="Show a link of all server's leaderboard",pass_context=True)
    async def server_level_link(self,msg):
        await self.bot.says_edit("Check this out!\nhttp://nurevam.site/server/levels".format(msg.message.server.id))

    @commands.command(name="rank",brief="Allow to see what rank you are at",pass_context=True)
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
        await self.bot.say_edit("```xl\n{}: Level: {} | EXP: {}/{} | Total XP: {} | Rank: {}/{}\n```".format(player.display_name,player_data["Level"],
                                                                                                                     player_data["XP"],player_data["Next_XP"],
                                                                                                                     player_data["Total_XP"],player_rank,len(data)))
        cooldown = await self.redis.hget("{}:Level:Config".format(server),"rank_cooldown")
        if cooldown is None:
            return
        if int(cooldown) == 0:
            return
        await self.redis.set("{}:Level:{}:rank:check".format(server,msg.message.author.id),'cooldown',expire=int(cooldown))

    @commands.command(name="table",brief="Allow to see top 10 rank",pass_context=True)
    async def rank_table(self,msg):
        server = msg.message.server.id
        player_data = await  self.redis.sort("{}:Level:Player".format(server),"{}:Level:Player:*->ID".format(server),
                                                                             "{}:Level:Player:*->Level".format(server),
                                                                             "{}:Level:Player:*->XP".format(server),
                                                                             "{}:Level:Player:*->Next_XP".format(server),
                                                                             "{}:Level:Player:*->Total_XP".format(server),
                                                                             by="{}:Level:Player:*->Total_XP".format(server),offset=0,count=-1)
        player_data=list(reversed(player_data))
        table = PrettyTable()
        table.field_names=["Rank","Name","Level","EXP","Total EXP"]
        table.align["Name"]='l'
        table.align["Level"] ='r'
        table.align["EXP"]='r'
        table.align["Total EXP"]='r'
        counter = 0
        for x in range(0,len(player_data),5):
            counter += 1
            exp = "{}/{}".format(player_data[x+2],player_data[x+1])
            name = msg.message.server.get_member(player_data[x+4]).display_name
            table.add_row([counter,name,player_data[x+3],exp,player_data[x]])
            if counter == 10:
                break
        table.vertical_char="│"
        table.horizontal_char="─"
        table.junction_char="┼"
        await self.bot.says_edit("```xl\n{}\n```".format(table))

def setup(bot):
    bot.add_cog(Level(bot))
