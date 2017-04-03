import redis as rdb
import platform
import aiohttp
import json

#############Color for Terminal###############################
#Whole line, and easier to debug
def prRed(prt): print("\033[91m{}\033[00m".format(prt))
def prGreen(prt): print("\033[92m{}\033[00m".format(prt))
def prYellow(prt): print("\033[93m{}\033[00m".format(prt))
def prLightPurple(prt): print("\033[94m {}\033[00m".format(prt))
def prPurple(prt): print("\033[95m{}\033[00m".format(prt))
def prCyan(prt): print("\033[96m{}\033[00m".format(prt))
def prLightGray(prt): print("\033[97m{}\033[00m".format(prt))
def prBlack(prt): print("\033[98m{}\033[00m".format(prt))
###############################################################

if platform.system() == "Windows": #due to different path for linux and window
    path = "..\\secret.json"
else:
    path = "/home/mave/Nurevam/secret.json"
#read files and save it to secret
with open (path,"r",encoding = "utf8") as f:
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
        print(db_role)
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
    with aiohttp.ClientSession() as session:
        async with session.post("https://hastebin.com/documents",data = str(info)) as resp:
            if resp.status is 200:
                return "https://hastebin.com/{}.py".format((await resp.json())["key"])
