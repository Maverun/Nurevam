import redis
import os
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

def OS_Get(name):
    return os.environ.get(name)

#########################################
#    _____               _   _          #
#   |  __ \             | | (_)         #
#   | |__) |   ___    __| |  _   ___    #
#   |  _  /   / _ \  / _` | | | / __|   #
#   | | \ \  |  __/ | (_| | | | \__ \   #
#   |_|  \_\  \___|  \__,_| |_| |___/   #
#                                       #
#########################################

###########Connection Line####################
def redis_connection():
    global redis
    redis = redis.Redis(host=OS_Get("Redis"),decode_responses=True)

############Checking if cogs for that server is enable or disable##########
def is_enable(msg,Cogs):
    data = redis
    try:
        check = data.hget("{}:Config:Cogs".format(msg.message.server.id),Cogs)
        if check == "on":
            return True
        else:
            return False
    except:
        return False
    pass

######################Checking if Role is able######################################
def check_roles(msg,Cogs,Get_Roles):
    data = redis
    try:
        Roles= data.smembers("{}:{}:{}".format(msg.message.server.id,Cogs,Get_Roles))
        checking=msg.message.author.roles
        for name in checking:
            for role in Roles:
                if role == name.id:
                    return True
    except Exception as e:
        prRed("ERROR\n{}".format(e))
        return False
#####################Checking if it cooldown#####################################
def is_cooldown(msg):
    return redis
