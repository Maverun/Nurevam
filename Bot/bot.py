from discord.ext import commands
from cogs.utils import utils
import datetime
import glob
import storage
import discord
import traceback
import asyncio
import inspect
import re


description = '''Nurevam's Command List. '''
bot = commands.Bot(command_prefix=commands.when_mentioned_or("$"), description=description,pm_help=False)
bot.db= storage.Redis()

async def say_edit(msg):
    key = str(inspect.getmodule(inspect.currentframe().f_back.f_code))
    regex = re.compile(r"(cogs.[a-zA-Z]*)")
    get = re.search(regex,key)
    if get:
        word = await bot.say(msg)
        check = await bot.db.redis.hgetall("{}:Config:Delete_MSG".format(word.server.id))
        if len(check)>0:
            if check[get.groups()[0][5:]] == "on":
                await asyncio.sleep(30)
                await bot.delete_message(word)
    else:
        print("NONE")
    return

bot.says_edit=say_edit

@bot.event
async def on_ready():
    print('Logged in')
    print(bot.user.id)
    print('------')
    if not hasattr(bot, 'uptime'):
            bot.uptime = datetime.datetime.utcnow()
    utils.redis_connection()
    load_cogs()

@bot.event
async def on_message(msg): #For help commands.
    try:
        cmd_prefix= (await bot.db.redis.get("{}:Config:CMD_Prefix".format(msg.server.id)))
        cmd_prefix=cmd_prefix.split(",")
        if '' in cmd_prefix: #check if "none-space" as a command, if true, return, in order to prevert any spam in case, lower chance of getting kick heh.
            return
        bot.command_prefix = commands.when_mentioned_or(*cmd_prefix)
        if "help" in msg.content:
            if await bot.db.redis.get("{}:Config:Whisper".format(msg.server.id)) == "on":
                bot.pm_help =True
            else:
                bot.pm_help=False
    except:
        pass

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
            # continue
            # raise

def list_cogs():
    cogs = glob.glob("cogs/*.py")
    clean = []
    for c in cogs:
        c = c.replace("/", "\\") # Linux fix
        if "__init__" in c:
            continue
        clean.append("cogs." + c.split("\\")[1].replace(".py", ""))
    return clean

async def send_cmd_help(ctx):
    if ctx.invoked_subcommand:
        pages = bot.formatter.format_help_for(ctx,ctx.invoked_subcommand)
        for page in pages:
            await bot.send_message(ctx.message.channel, page.replace("\n","fix\n",1))
    else:
        pages = bot.formatter.format_help_for(ctx,ctx.command)
        for page in pages:
            await bot.send_message(ctx.message.channel,page.replace("\n","fix\n",1))

@bot.event
async def on_command_error(error,ctx):
    # print(error)
    # print(ctx.message.clean_content)
    if isinstance(error, commands.MissingRequiredArgument):
        await send_cmd_help(ctx)
    elif isinstance(error,commands.BadArgument):
        await send_cmd_help(ctx)

@bot.event
async def on_error(event,*args,**kwargs):
    Current_Time = datetime.datetime.utcnow().strftime("%b/%d/%Y %H:%M:%S UTC")
    utils.prRed(Current_Time)
    utils.prRed("Error!")
    utils.prRed(traceback.format_exc())
    error =  '```py\n{}\n```'.format(traceback.format_exc())
    await bot.send_message(bot.get_channel("123934679618289669"), "```py\n{}```".format(Current_Time + "\n"+ "ERROR!") + "\n" +  error)



if __name__ == '__main__':
    bot.run(utils.OS_Get("NUREVAM_TOKEN"))

