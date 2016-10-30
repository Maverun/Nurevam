import random
from . import utils
from prettytable import PrettyTable
import prettytable
import discord

class Utils_rpg():
    def __init__(self,redis,server,play_objec,data,ctx=None,bot=None):
        #RPG Variable
        self.redis=redis
        self.ctx=ctx
        self.server=server
        self.player = play_objec
        self.player_id=self.player.id
        self.credit= int(data.get("credit",100))
        self.health = int(data.get("hp",100))
        self.total_health = self.health
        self.mana = int(data.get("mana",100))
        self.total_mana = self.mana
        self.data = data
        self.profile="{}:Rpg:{}:".format(server,self.player.id) + "{}"
        self.bot = bot
        self.table = PrettyTable()
        self.table.hrules=prettytable.ALL
        self.table.vertical_char="│"
        self.table.horizontal_char="─"
        self.table.junction_char="┼"
        # print(data)

    async def _credit(self):
        self.credit = await self.redis.hget(self.profile.format("Profile"),"credit")
        return self.credit

    async def deposit(self,amount):
        await self.redis.hincrbyfloat(self.profile.format("Profile"),"credit",increment=amount)

    async def withdraw(self,amount):
        await self.redis.hincrbyfloat(self.profile.format("Profile"),"credit",increment=-amount)

    def lose_hp(self,amount):
        self.health -=amount

    def gain_hp(self,amount):
        self.health +=amount

    #if bool is True, it is gain, if false, it is loss
    def lose_gain_hp(self,amount,bool):
        print(amount,bool)
        if self.health-amount <= 100 and self.health>0 and bool is False:
          print("LOSE HP!")
          self.health-=amount
          print(self.health)
        elif self.health+amount>self.total_health and bool:
          self.health = self.total_health
        elif not self.health+amount > self.total_health and bool:
          self.health += amount
        else:
          return False

    #get info of mob for fight!
    def mob(self,info):
        # print(info)
        self.mob_name=info["name"]
        self.mob_level=int(info["level"])
        self.mob_hp=int(info["hp"])
        self.mob_total_hp = self.mob_hp
        self.mob_mana=int(info.get("mana",1))
        self.mob_total_mana = self.mob_mana
        self.mob_str=int(info.get("str",1))
        self.mob_int=int(info.get("int",1))
        self.mob_def=int(info["def"])
        self.mob_magic_def=int(info["magic_def"])
        self.mob_agility = int(info["agility"])

    def check_hp(self,player=True):
        """

        Args:
            player: True if it player, else Mob

        Returns:
            Checking if hp is above, if so, return True or else False
        """
        """
        If bool is true it will check player
        else if it false, it will check mob
        if hp is below 0, it will return True
        else it will be return False
        """
        if player:
            utils.prYellow("Player hp is {}".format(self.health))
            if self.health < 0:
                return True
        else:
            utils.prYellow("Mob hp is {}".format(self.mob_hp))
            if self.mob_hp < 0:
                return True
        return False

    def chance_attack_flee(self):
        """
        If both mob and player level are same
        get a chance 50%, if True, attack
        or else, mob or player will dodge
        other wise if not same level
        get both agility mob and user
        get start point by finding differences of mob and player's agility
        then find a random of mob/player agility
        if greater than chance, then return True to attack
        or else False for dodge

        While it is also Flee as as well

        """
        if self.mob_level == self.data["level"]:
            if random.randint(0,1) == 1:
                return True
        else:
            agility = int(self.data["agility"])
            start_point = abs(self.mob_agility-agility)
            chance = random.randint(min([self.mob_agility,agility]),max([self.mob_agility,agility]))
            # print("CHANCE ATTACK")
            # print(start_point)
            # print(chance)
            if start_point > chance:
                return True
        return False

    def attack_mob_melee(self):
        start_point =  int(self.data["str"]) * int(self.data["weapon_att"])
        hit = random.randint(start_point-5,start_point+5)
        hit_point = abs(self.mob_def - hit) #so even if it negative, will be alway postives
        self.mob_hp -= hit_point
        utils.prRed("HIT IS {}".format(hit_point))
        return hit_point

    def attack_mob_magic(self):
        if self.mana > 0:
            start_point =  int(self.data["int"]) * int(self.data["weapon_int"])
            hit = random.randint(start_point-5,start_point+5)
            hit_point = abs(self.mob_magic_def - hit)
            self.mob_hp -= hit_point
            self.mana -= 10
            return hit_point
        else:
            return False
    def attack_player_melee(self):
        start_point =  self.mob_str
        hit = random.randint(start_point-5,start_point+5)
        hit_point = abs(int(self.data["def"]) - hit) #so even if it negative, will be alway postives
        self.health -= hit_point
        return hit_point

    def attack_player_magic(self):
        if self.mob_mana > 0:
            start_point =  self.mob_int
            hit = random.randint(start_point-5,start_point+5)
            hit_point = abs(int(self.data["magic_def"]) - hit)
            self.mob_hp -= hit_point
            self.mob_mana -= 10
            return hit_point
        else:
            return False

    async def player_item(self):
        def digit_check(num):  # to ensure that answer is int
            return num.content.isdigit()
        message = []
        await self.list_item()
        message.append(await self.bot.say("```\n{}\n```".format(self.show_item())))
        message.append(await self.bot.say("Which item"))
        msg = await self.bot.wait_for_message(timeout=15, author=self.player, check=digit_check)
        message.append(msg)
        await self.bot.delete_messages(message)
        return await self.use_item(msg.content)

    async def player_attack(self,num):
        """
        It will check player's choice
        if it 1, it mean player want a meele time
        if it 2, it mean player want a magic time
        if it 4, it mean player want a salty escape.
        """
        chance = self.chance_attack_flee()
        if chance:
            if num == "1":
                return "```diff\n+You deal {}\n```".format(self.attack_mob_melee())
            elif num == "2":
                result = self.attack_mob_magic()
                if result:
                    return "```diff\n+You cast a spell and deal {}!\n```".format(result)
                else:
                    return "```diff\n-You went out of mana!\n```"
            elif num == "3":
                return await self.player_item()
            elif num == "4":
                return "```diff\n-You have escape from the battle!\n```".format(self.chance_attack_flee())
        else:
            if num == "4":
                return "```diff\n-You failed to escape!\n```"
            else:
                return "```diff\n-You missed!\n```"


    def battle_mob_table(self):
        """
        To make a nice table to show a stats
        """
        table = self.table.copy()
        player_hp="{}/{}".format(self.health,self.total_health)
        mob_hp="{}/{}".format(self.mob_hp,self.mob_total_hp)
        player_mana = "{}/{}".format(self.mana,self.total_mana)
        mob_mana = "{}/{}".format(self.mob_mana,self.mob_total_mana)
        table.field_names=["","Player","Mob"]
        table.add_row(["Name",self.ctx.message.author.name,self.mob_name])
        # table.add_row(["Level",self.player_level])
        table.add_row(["HP",player_hp,mob_hp])
        table.add_row(["Mana",player_mana,mob_mana])
        return table


#######################################################################
##########     _____                 _                       ##########
##########    / ____|               | |                      ##########
##########   | (___    _   _   ___  | |_    ___   _ __ ___   ##########
##########    \___ \  | | | | / __| | __|  / _ \ | '_ ` _ \  ##########
##########    ____) | | |_| | \__ \ | |_  |  __/ | | | | | | ##########
##########   |_____/   \__, | |___/  \__|  \___| |_| |_| |_| ##########
##########              __/ |                                ##########
##########             |___/                                 ##########
#######################################################################

#########################################
#    _                              _   #
#   | |                            | |  #
#   | |        ___  __   __   ___  | |  #
#   | |       / _ \ \ \ / /  / _ \ | |  #
#   | |____  |  __/  \ V /  |  __/ | |  #
#   |______|  \___|   \_/    \___| |_|  #
#########################################



    async def get_exp_mob(self):
        """
        It will calculate the exp from mob
        It used level's require exp to next level up
        with is 100* 1.2**mob level at this moment
        Then using lowest range 5% and highest range 7%
        to get RNG exp
        """
        utils.prPurple("Checking EXP earn")
        next_exp= int(100 * (1.2 ** self.mob_level))
        first_range = next_exp * 0.05
        second_range = next_exp *0.07
        utils.prGreen("{},{}".format(first_range,second_range))
        self.gain_exp= random.randint(int(first_range),int(second_range))
        return self.gain_exp

    async def put_exp(self):
        await self.redis.hincrbyfloat("{}:Level:Player:{}".format(self.server,self.player_id),"XP",increment=self.gain_exp)
        return await self.check_level()

    async def check_level(self):
        """
        It will check if player's exp is above require exp
        If it so, it will increase level by 1 and new equations for next levels
        """
        key = "{}:Level:Player:{}".format(self.server,self.player_id)
        info = await self.redis.hgetall(key)
        print(info)
        if int(info["XP"]) >= int(info["Next_XP"]):
            xp = int(info["XP"]) - int(info["Next_XP"])
            next_exp = int(100 * (1.2 ** int(info["level"])))
            await self.redis.hset(key,"Next_XP", next_exp)
            await self.redis.hset(key,"XP",xp)
            await self.redis.hincrby(key,"Level",increment=1)
            await self.check_town_requirement() #Checking Town requirement, so player cant join old one and join new one.
            return True
        return False

######################################
#    _____   _                       #
#   |_   _| | |                      #
#     | |   | |_    ___   _ __ ___   #
#     | |   | __|  / _ \ | '_ ` _ \  #
#    _| |_  | |_  |  __/ | | | | | | #
#   |_____|  \__|  \___| |_| |_| |_| #
######################################

    async def list_item(self):
        """
        Check a player's inventory and return a list of item.
        Returns:
            A list of item.
        """
        info_item = await self.redis.hgetall(self.profile.format("Item"))
        get_item = "{}:Rpg:Item:".format(self.server) + "{}"
        self.item = {}
        for x in info_item:
            print(x)
            print(get_item.format(x))
            info = await self.redis.hgetall(get_item.format(x))
            info.update({"total":info_item[x]})
            self.item.update({x:info})
        return self.item

    def show_item(self):
        table = self.table.copy()
        table.field_names=["","Item","Stack"]
        table.add_row(([0,"Return",""]))
        self.item_id = {}
        for x,elem in enumerate(self.item):
            print(x)
            item = self.item[elem]["name"]
            total = self.item[elem]["total"]
            utils.prPurple(elem)
            table.add_row([x+1,item,total])
            self.item_id.update({x+1:elem})
        return table

    def which_type(self,item):
        if item["type"] == "hp":
            number = int(item["hp"])
            if self.health >= self.total_health:
                return "```diff\n-You already at full hp!\n```"
            elif self.health + number >= self.total_health:
                number = self.total_health-self.health
                self.health = self.total_health
            else:
                self.health += number
            return "```diff\n+You gained {} hp!\n```".format(number)

        pass

    async def use_item(self,item_ids):
        utils.prYellow(self.item_id)
        print(item_ids)
        what_item = self.item_id[int(item_ids)]
        self.redis.hincrby(self.profile.format("Item"),what_item,increment=-1)
        if 0 >= int(self.item[what_item]["total"])-1:
            print("delete!")
            await self.redis.hdel(self.profile.format("Item"),what_item)
        return self.which_type(self.item[what_item])

    def generate(self,x):
        stat = random.choice([0.1,1,1.5])
        dmg = x * stat
        result = random.randint(int(dmg-5),int(dmg+5))
        if result <=0:
            return self.generate(x)
        else:
            return result

    def create_equip(self):
        type = random.choice(["meele","magic"])
        equip = {}
        level = self.mob_level
        if type == "meele":
            result = self.generate(self.mob_str)
            equip={"patk":result,"level":level}
        elif type == "magic":
            result = self.generate(self.mob_int)
            equip={"matk":result,"level":level}
        return equip



#################################
#    _______                    #
#   |__   __|                   #
#      | | _____      ___ __    #
#      | |/ _ \ \ /\ / / '_ \   #
#      | | (_) \ V  V /| | | |  #
#      |_|\___/ \_/\_/ |_| |_|  #
#################################

    async def check_town_requirement(self):
        #getting player level
        level = self.data["level"]
        #we are setting up channel permission
        allow = discord.Permissions.none()
        allow.read_messages = True
        allow.send_message = True
        deny = discord.Permissions.none()
        deny.read_messages = False
        deny.send_message = False
        #Getting info which town that player can visit
        player_town_list = await self.redis.smembers("0.message.server.id}:Rpg:{0.message.author.id}:Town".format(self.ctx))
        #Geting all town info.
        town_list = await self.redis.smembers("0.message.server.id}:Rpg:Town".format(self.ctx))
        for x in town_list:
            print(x)
            data = await self.redis.hgetall("0.message.server.id}:Rpg:Town:{1}".format(self.ctx,x))
            if x in player_town_list: #checking if it already in player data
                if level > data["max_level"]: #If it above that max level, town will be gone from player.
                    await self.bot.edit_channel_permission(self.bot.get_channel(data["id"],self.player,deny))
                    await self.redis.srem("0.message.server.id}:Rpg:{0.message.author.id}:Town".format(self.ctx),x)
                    continue
            if level >= data["min_level"] and level <= data["max_level"]:
                await self.bot.edit_channel_permission(self.bot.get_channel(data["id"], self.player, allow))
                await self.redis.sadd("0.message.server.id}:Rpg:{0.message.author.id}:Town".format(self.ctx),x)


#############################
#    ______                 #
#   |___  /                 #
#      / / ___  _ __   ___  #
#     / / / _ \| '_ \ / _ \ #
#    / /_| (_) | | | |  __/ #
#   /_____\___/|_| |_|\___| #
#############################




