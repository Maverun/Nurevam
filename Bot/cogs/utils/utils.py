import redis as rdb
import traceback
import datetime
import platform
import aiohttp
import asyncio
import json

#############Color for Terminal###############################
#Whole line, and easier to debug
def prRed(prt): print("\033[91m{}\033[00m".format(prt))
def prGreen(prt): print("\033[92m{}\033[00m".format(prt))
def prYellow(prt): print("\033[93m{}\033[00m".format(prt))
def prLightPurple(prt): print("\033[94m{}\033[00m".format(prt))
def prPurple(prt): print("\033[95m{}\033[00m".format(prt))
def prCyan(prt): print("\033[96m{}\033[00m".format(prt))
def prLightGray(prt): print("\033[97m{}\033[00m".format(prt))
def prBlack(prt): print("\033[98m{}\033[00m".format(prt))
###############################################################

#read files and save it to secret
with open ("../secret.json","r",encoding = "utf8") as f:
    secret = json.load(f)

###########Connection Line####################
redis = rdb.Redis(host=secret["Redis"], decode_responses=True)

def is_owner(ctx): #Checking if you are owner of bot
    return ctx.message.author.id == 105853969175212032

############Checking if cogs for that guild is enable or disable##########
def is_enable(ctx,cog):
    try:
        return redis.hget("{}:Config:Cogs".format(ctx.message.guild.id),cog) == "on"
    except:
        return False

######################Checking if Role is able######################################
def check_roles(ctx,cog,get_role): #Server ID  then which plugin, and Roles with set
    try:
        db_role= redis.smembers("{}:{}:{}".format(ctx.message.guild.id,cog,get_role))
        print("Roles: ",db_role)
        author_roles= [role.id for role in ctx.message.author.roles]
        print(author_roles)
        for role in db_role:
            print(role)
            if int(role) in author_roles:
                return True
        return False
    except Exception as e:
        prRed("ERROR\n{}".format(e))
        return False

async def send_hastebin(info):
    async with aiohttp.ClientSession() as session:
        async with session.post("https://hastebin.com/documents",data = str(info)) as resp:
            if resp.status == 200:
                return "https://hastebin.com/{}.py".format((await resp.json())["key"])

async def input(bot,ctx,msg,check):
    """

    Args:
        ctx: discord Context
        msg: Message to send to users
        check: conditions accept from user.

    Returns: return message object from user's

    """
    asking = await ctx.send(msg) #sending message to ask user something
    try:
        answer = await bot.wait_for("message", timeout=15, check=check)
        await answer.delete()
    except asyncio.TimeoutError:  # timeout error
        await asking.delete()
        await ctx.send(content="You took too long, please try again!",delete_after = 15)
        return None
    except:
        pass
    await asking.delete()  # bot delete it own msg.
    return answer

class Background:
    """
    Background, allow to run auto background task easily without worry.
    """

    current = datetime.datetime.utcnow() #datetime obj

    def __init__(self,name,max_time,sleep_time,function,log):
        self.name = name
        self.max_time = max_time
        self.sleep_time = sleep_time
        self.function = function #function to call
        self.log = log
        self.current = datetime.datetime.utcnow()

    def start(self): #to start function run
        loop = asyncio.get_event_loop()
        self.loop_timer = loop.create_task(self.timer())
        prLightPurple("Starting {} loop".format(self.name))

    def stop(self):
        self.loop_timer.cancel()
        prLightPurple("Stopping {} loop".format(self.name))


    async def timer(self):
        try:
            while True:
                self.current = datetime.datetime.utcnow()
                self.log.debug(self.current)
                self.log.debug("Calling event")
                await self.function()
                self.log.debug("Enter sleep mode")
                await asyncio.sleep(self.sleep_time)
        except asyncio.CancelledError:
            return prRed("Asyncio Cancelled Error")
        except Exception as e:
            print(e)
            prRed(traceback.format_exc())

class Embed_page:
    """
    Embed page, with reaction to go next or now (or other reaction for certain feature)
    """

    def __init__(self,bot,embed_list,**kwargs):
        self.bot = bot
        self.embed_page = embed_list #expecting list of embed
        self.max_page = kwargs.get("max_page",len(embed_list))
        self.page = kwargs.get("page",0) #current page, default is 0
        self.alt_edit = kwargs.get("alt_edit") #if wish to edit message AFTER return function that is not belong here
        self.original_msg = kwargs.get("original_msg") #^
        #this is array with emotion:function, so we can have each reaction for certain function. Reason for array is order
        self.reaction = kwargs.get("reaction", [[u"\u2B05",self.back_page],[u"\u27A1",self.continue_page]])


    def back_page(self,*args):
        self.page -= 1
        if self.page -1 <= 0:
           self.page = 0 #dont change it
        return self.page

    def continue_page(self,*args):
        self.page += 1
        if self.page > self.max_page - 1:
            self.page = self.max_page - 1
        return self.page

    def get_page(self):
        return self.embed_page[self.page]

    async def wait_for_react(self,check,timeout):
        try:
            reaction, user = await self.bot.wait_for("reaction_add", timeout = timeout, check = check)
        except asyncio.TimeoutError:
            return None,None
        else:
            return reaction,user

    async def start(self,channel,check,timeout = 60,is_async = False,extra = []):
        """
        
        Args:
            channel: discord.channel. A destination to send message.
            check : checking permission for this.
            timeout: timeout for message to run if no one rect. Default 60 second
        
        It will send message or edit message if original_msg exist. To get that, you will need to pass self.alt_edit True and rerun this template.
        Run iterate of self.reaction for adding rect into it
        Then finally run endless loops waiting for message etc
        """
        if self.original_msg:
            await self.original_msg.edit(embed = self.get_page())
            self.message = self.original_msg
        else:
            self.message = await channel.send(embed = self.get_page())

        for rect in self.reaction:
            await self.message.add_reaction(rect[0])

        while True:
            react,user = await self.wait_for_react(check,timeout)
            #If react is none, it mean that it had reach timeout and user didn't react.
            if react is None:
                return await self.message.clear_reactions()
            #remove user's message
            try:

                await self.message.remove_reaction(react.emoji,user)
            except: #if bot does not have permission for it. Oh well. Hard time for user.
                pass

            #now we will find reaction it used and then run function of that.
            #once we do that, we will delete that reaction.

            for item in self.reaction:
                if item[0] == react.emoji: #if it equal then we can call function
                    if is_async:
                        if self.alt_edit:
                            await item[1](react,user,self.message,*extra)
                        else:
                            await item[1](react,user,*extra)
                    else:
                        if self.alt_edit:
                            item[1](react,user,self.message,*extra)
                        else:
                            item[1](react,user,*extra)
                    break

            #now we will update message again
            await self.message.edit(embed = self.get_page())

