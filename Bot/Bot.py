from discord.ext import commands
from Cogs.Utils import Read,Utils
import datetime
import glob
import Storage
import discord
import traceback
import sys


Config=Read.config
description = '''{} bot Command List. '''.format(Config["Bot name"])
bot = commands.Bot(command_prefix=commands.when_mentioned_or("$"), description=description,pm_help=Config["PM_Help"])

@bot.event
async def on_ready():
    print('Logged in')
    print(bot.user.id)
    print('------')
    bot.uptime = datetime.datetime.utcnow()
    load_cogs()
    await Storage.Redis().Save()

def get_bot_uptime():
    now = datetime.datetime.utcnow()
    delta = now - bot.uptime
    hours, remainder = divmod(int(delta.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    days, hours = divmod(hours, 24)
    if days:
        fmt = '**{d}** days, **{h}** hours, **{m}** minutes, and **{s}** seconds'
    else:
        fmt = '**{h}** hours, **{m}** minutes, and **{s}** seconds'

    return fmt.format(d=days, h=hours, m=minutes, s=seconds)

@bot.command()
async def uptime(): #Showing Time that bot been total run
    """Tells you how long the bot has been up for."""
    await bot.say("I've been up for {}".format(get_bot_uptime()))

def load_cogs():
    cogs = list_cogs()
    for cogs in cogs:
        try:
            bot.load_extension(cogs)
            print ("Load {}".format(cogs))
        except Exception as e:
            Utils.prRed(cogs)
            print(e)
            raise

def list_cogs():
    cogs = glob.glob("Cogs/*.py")
    clean = []
    for c in cogs:
        c = c.replace("/", "\\") # Linux fix
        if "__init__" in c:
            continue
        clean.append("Cogs." + c.split("\\")[1].replace(".py", ""))
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
    print(error)
    print(ctx.message.content)
    if isinstance(error, commands.MissingRequiredArgument):
        await send_cmd_help(ctx)
    elif isinstance(error,commands.BadArgument):
        await send_cmd_help(ctx)

@bot.event
async def on_command(command,ctx):
    # print(ctx.message.content)
    pass

@bot.event
async def on_error(event,*args,**kwargs):
    Utils.prRed("Error!")
    print(event)
    print(*args)
    print(**kwargs)
    Utils.prCyan(sys.exc_info())
    Current_Time = datetime.datetime.utcnow().strftime("%b/%d/%Y %H:%M:%S UTC")
    Utils.prGreen(Current_Time)
    Utils.prRed(traceback.format_exc())
    error =  '```py\n{}\n```'.format(traceback.format_exc())
    await bot.send_message(bot.get_channel("123934679618289669"), "```py\n{}```".format(Current_Time + "\n"+ "ERROR!") + "\n" +  error)


if __name__ == '__main__':
    bot.run(Config['password'])

