from discord.ext import commands
from cogs.utils import utils
import traceback
import datetime
import storage
import discord
import inspect
import glob
import re

description = '''Nurevam's Command List. '''
bot = commands.Bot(command_prefix=commands.when_mentioned_or("!"), description=description,help_attrs=dict(pm_help=False,hidden=True))
bot.db= storage.Redis()
redis = utils.redis

def check_post(check):
    if check == "None":
        return None
    elif check == "on":
        return 30

def get_channel(name):
    stack = inspect.stack()
    try:
        for frames in stack:
            try:
                frame = frames[0]
                current_locals = frame.f_locals
                if name in current_locals:
                    return current_locals[name]
            finally:
                del frame
    finally:
        del stack

async def say_edit(msg = None,embed = None):
    try:
        key = str(inspect.getmodule(inspect.currentframe().f_back.f_code))
        regex = re.compile(r"(cogs.[a-zA-Z]*)")
        get = re.search(regex,key)
        if get:
            check = await bot.db.redis.hgetall("{}:Config:Delete_MSG".format(get_channel("_internal_channel").server.id))
            check = check.get(get.groups()[0][5:])
            await bot.say(content = msg,embed = embed,delete_after=check_post(check))
        return
    except:
        utils.prRed(traceback.format_exc())
bot.says_edit=say_edit

@bot.event
async def on_ready():
    print('Logged in')
    print(bot.user.id)
    print('------')
    if not hasattr(bot, 'uptime'):
        bot.uptime = datetime.datetime.utcnow()
        bot.owner = (await bot.application_info()).owner
        bot.background = {}
        bot.id_discourse = 0
        load_cogs()
    await bot.change_presence(game = discord.Game(name="http://nurevam.site/"))

async def command_checker(msg):
    try:
        if bot.user.id == "181503794532581376":
            bot.command_prefix = commands.when_mentioned_or("$")
            bot.pm_help = False
            return
        cmd_prefix= (await bot.db.redis.get("{}:Config:CMD_Prefix".format(msg.server.id)))
        cmd_prefix=cmd_prefix.split(",")
        if '' in cmd_prefix: #check if "none-space" as a command, if true, return, in order to prevert any spam in case, lower chance of getting kick heh.
            return
        bot.command_prefix = commands.when_mentioned_or(*cmd_prefix)
        if "help" in msg.content: #changing setting for help, if server owner want Help command to be via PM or to server.
            if await bot.db.redis.get("{}:Config:Whisper".format(msg.server.id)) == "on":
                bot.pm_help =True
            else:
                bot.pm_help=False
    except:
        pass

@bot.event
async def on_message(msg): #For help commands and custom prefix.
    await command_checker(msg)
    await bot.process_commands(msg)

@bot.event
async def on_message_edit(before,msg): #get command from edit message with same feature as on_message..
    await command_checker(msg)
    await bot.process_commands(msg)

def load_cogs():
    cogs = list_cogs()
    for cogs in cogs:
        try:
            bot.load_extension(cogs)
            print ("Load {}".format(cogs))
        except Exception as e:
            utils.prRed(cogs)
            utils.prRed(e)

def list_cogs():
    cogs = glob.glob("cogs/*.py")
    clean = []
    for c in cogs:
        c = c.replace("/", "\\") # Linux fix
        if "__init__" in c:
            continue
        clean.append("cogs." + c.split("\\")[1].replace(".py", ""))
    return clean

@bot.event
async def on_error(event,*args,**kwargs):
    print(event)
    print(args)
    print(kwargs)
    Current_Time = datetime.datetime.utcnow().strftime("%b/%d/%Y %H:%M:%S UTC")
    utils.prRed(Current_Time)
    utils.prRed("Error!")
    utils.prRed(traceback.format_exc())
    error =  '```py\n{}\n```'.format(traceback.format_exc())
    await bot.send_message(bot.owner, "```py\n{}```".format(Current_Time + "\n"+ "ERROR!") + "\n" + error)

if __name__ == '__main__':
    bot.run(utils.secret["nurevam_token"])
