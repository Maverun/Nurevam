from discord.ext import commands
from random import randint
from .Utils import Utils
import asyncio
import discord
import Storage
import time
import json

def is_enable(msg):
    check = Storage.Redis().data.hget("{}:Config".format(msg.message.server.id),"Level")
    if check == "on":
        return True
    else:
        return False

class Level():
    def __init__(self,bot):
        self.bot = bot
        loop = asyncio.get_event_loop()
        loop.create_task(self.Redis())
        self.bot.add_listener(self.message,"on_message")

    async def Redis(self):#To call Redis so it can begin data.
        self.redis = await Storage.Redis().data

    async def message(self,msg): #waiting for player reply
        if msg.author == self.bot.user:
            return
        if msg.channel.is_private:
            return
        if await self.redis.hget("{}:Config".format(msg.server.id),"Level") == "off":
            return
        player = msg.author.id
        server = msg.server.id
        await self.redis.set('{}:Level:Server_Name'.format(server),msg.server.name)
        await self.redis.set('{}:Level:Server_Icon'.format(server),msg.server.icon)
        self.name="{}:Level:Player:{}".format(server,player)
        list = await self.redis.exists(self.name) #Call of name and ID to get boolean
        if list is False: # if it False, then it will update a new list for player who wasnt in level record
            await self.New_profile(msg)
        await self.redis.hincrby(self.name,"Total Message Count",amount=1)
        await self.redis.hset(self.name,"ID",player)
        await self.redis.hset(self.name,"Name",msg.author.name)
        check = await self.redis.get("{}:check".format(self.name))
        if check: #If it true, return, it haven't cool down yet
            return
        await self.redis.sadd("{}:Level:Player".format(server),player)
        await self.redis.hset(self.name,"Discriminator",msg.author.discriminator)
        await self.redis.hset(self.name,"Avatar",msg.author.avatar)
        xp = randint(5,10)
        await self.redis.hincrby(self.name,"XP",amount=(xp))
        await self.redis.hincrby(self.name,"Total_XP",amount=(xp))
        await self.redis.hincrby(self.name,"Message Count",amount=1)
        Current_XP=await self.redis.hget(self.name,"XP")
        Next_XP=await self.redis.hget(self.name,"Next_XP")
        Utils.prCyan(Next_XP)
        if int(Current_XP) >= int(Next_XP):
            level = await self.redis.hget(self.name,"Level")
            traits_check =await self.redis.hget("{}:Level:Trait".format(server),"{}".format(level))
            if traits_check is not None:
                traits = traits_check
            else:
                traits = randint(1,3)
            Remain_XP = int(Current_XP) - int(Next_XP)
            await self.Next_Level(Remain_XP)
            await self.redis.hset("{}:Level:Trait".format(server),level,traits)
            await self.redis.hincrby(self.name,"Total Traits Points",amount=traits)
            print("{} Level up!".format(msg.author))
            # self.redis.set("{}:Level:{}:check".format(server,player),'cooldown',ex=60)
        Utils.prGreen(await self.redis.sort("{}:Level:Player".format(server),by="{}:Level:Player:*->Total_XP".format(server),get=[
                                                                                                              "{}:Level:Player:*->Name".format(server),
                                                                                                              "{}:Level:Player:*->ID".format(server),
                                                                                                              "{}:Level:Player:*->Level".format(server),
                                                                                                              "{}:Level:Player:*->XP".format(server),
                                                                                                              "{}:Level:Player:*->Next_XP".format(server),
                                                                                                              "{}:Level:Player:*->Total_XP".format(server),
                                                                                                              "{}:Level:Player:*->Discriminator".format(server),
                                                                                                              "{}:Level:Player:*->Avatar".format(server),
                                                                                                              "{}:Level:Player:*->Total_Traits_Points"],start=0,num=100,desc=True))
    async def New_profile(self,msg):
        print ("New Profile!")
        await self.redis.hmset(self.name,
                         {"Name":msg.author,
                          "ID":msg.author.id,
                          "Level":1,
                          "XP":0,
                          "Next_XP":100,
                          "Total_XP":0,
                          "Message Count":0,
                          "Total Traits Points":0})

    async def Next_Exp(self,n):
        return int(100*(1.2**n))

    async def Next_Level(self,xp):
        level = await self.redis.hget(self.name,"Level")
        New_XP = await self.Next_Exp(int(level))
        await self.redis.hset(self.name,"Next_XP",(New_XP))
        await self.redis.hset(self.name,"XP",xp)
        await self.redis.hincrby(self.name,"Level",amount=1)

    @commands.command(name="rank",brief="Allow to see what rank you are at",pass_context=True)
    @commands.check(is_enable)
    async def rank(self,msg):
        startTime = time.time()
        if msg.message.mentions != []:
            player = msg.message.mentions[0]
        else:
            player = msg.message.author
        if await self.redis.exists("{}:Level:Player:{}".format(msg.message.server.id,player.id)) is False:
            if player != msg.message.author:
                await self.bot.say("{} seem to be not a ranked yet, Tell that person to talk more!".format(player.mention))
                return
            else:
                await self.bot.say("I am sorry, it seem you are not in a rank list! Talk more!")
                return
        print(player)
        counter =0
        rank_positon=1
        info = await self.redis.keys("{}:Level:Player:*".format(msg.message.server.id))
        player_Total_XP = await self.redis.hget("{}:Level:Player:{}".format(msg.message.server.id,player.id),"Total_XP")
        for num in info:
            if num != "{}:Level:Player:{}".format(msg.message.server.id,player.id):
                counter +=1
                compare=await self.redis.hget(num,"Total_XP")
                if int(player_Total_XP) <= int(compare):
                    rank_positon +=1
        Player_Data= await self.redis.hgetall("{}:Level:Player:{}".format(msg.message.server.id,player.id))
        await self.bot.say("```xl\n{}: Level: {} | EXP: {}/{} | Total XP: {} | Rank: {}/{} | Traits: {}\n```".format(player.name.lower(),Player_Data["Level"],
                                                                                                                     Player_Data["XP"],Player_Data["Next_XP"],
                                                                                                                     Player_Data["Total_XP"],rank_positon,counter,Player_Data["Total Traits Points"]))
        endTime=time.time()
        print("Took {} seconds to calculate.".format(endTime-startTime))

    @commands.command(name="table",brief="Allow to see top 10 rank",pass_context=True)
    @commands.check(is_enable)
    async def rank_table(self,msg):
        server = msg.message.server.id
        player_data =await  self.redis.sort("{}:Level:Player".format(server),by="{}:Level:Player:*->Total_XP".format(server),get=[
                                                                                                              "{}:Level:Player:*->Name".format(server),
                                                                                                              "{}:Level:Player:*->ID".format(server),
                                                                                                              "{}:Level:Player:*->Level".format(server),
                                                                                                              "{}:Level:Player:*->XP".format(server),
                                                                                                              "{}:Level:Player:*->Next_XP".format(server),
                                                                                                              "{}:Level:Player:*->Total_XP".format(server),
                                                                                                              "{}:Level:Player:*->Discriminator".format(server),
                                                                                                              "{}:Level:Player:*->Avatar".format(server),
                                                                                                              "{}:Level:Player:*->Total_Traits_Points"],start=0,num=10,desc=True)
        Total_Rank= len(self.redis.smembers("{}:Level:Player".format(server)))
        data = []
        counter=0
        for x in range(0,len(player_data),9):
            print (x)
            # temp = {
            #     "Name":player_data[x],
            #     "ID":player_data[x+1],
            #     "Level":int(player_data[x+2]),
            #     "XP":int(player_data[x+3]),
            #     "Next_XP":int(player_data[x+4]),
            #     "Total_XP":int(player_data[x+5]),
            #     "Discriminator":player_data[x+6],
            #     "Avatar":player_data[x+7],
            #     "Total_Traits":player_data[x+8]
            # }
            #Those are for Website
            counter+=1
            data.append("{}.{} Level: {} | EXP:{}/{} | Total XP: {} | Rank: {}/{}\n".format(counter,player_data[x],player_data[x+2],player_data[x+3],player_data[x+4],player_data[x+5],counter,Total_Rank))
        await self.bot.say("```xl\n{}\n```".format("".join(data)))

def setup(bot):
    bot.add_cog(Level(bot))