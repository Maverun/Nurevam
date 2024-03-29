from discord.ext import commands
from discord import errors
from cogs.utils import utils
import traceback
import datetime
import storage
import discord
import glob

import helpformat

description = '''Nurevam's Command List.
 To enable more commands, you must visit dashboard to enable certain plugins you want to run.
 If there is a problem with the prefix etc, please do @nurevam prefix to see what prefix you can do
 Any problem relating to Nurevam, please do contact owner Maverun (´･ω･`)#3333

 First └ mean it is commands under that plugin, and if there is one or more under commands, it is a sub command that can invoke by doing !parent subcommand such as !rank global
 '''
intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix=commands.when_mentioned_or("!"),
                   help_command=helpformat.Custom_format(),
                   description=description,
                   pm_help = False,
                   intents=intents,
                   hidden = True,)

bot.db= storage.Redis()
redis = utils.redis

def check_post(check):
    if check == "None":
        return None
    elif check == "on":
        return 30

async def say(ctx,**kwargs):
    print("at say function",ctx,kwargs)
    check = await bot.db.redis.hget("{}:Config:Delete_MSG".format(ctx.message.guild.id),ctx.command.cog_name.lower())
    return await ctx.send(**kwargs,delete_after=check_post(check))

bot.say=say

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
        bot.error_channel = bot.get_channel(823997727977111582)
        # bot.eng_lang = utils.read_lang("English")
        load_cogs()
    await bot.change_presence(activity = discord.Game("https://nurevam.site/"))

async def command_checker(msg):
    try:
        if isinstance(msg.channel,discord.DMChannel):
            if "!reply" in msg.content:
                bot.command_prefix = commands.when_mentioned_or("!")
                return

        if bot.user.id == 181503794532581376:
            bot.command_prefix = commands.when_mentioned_or("$")
            bot.pm_help = False
            return

        cmd_prefix = await bot.db.redis.get("{}:Config:CMD_Prefix".format(msg.guild.id)) or "!"
        cmd_prefix = cmd_prefix.split(",")
        if '' in cmd_prefix: #check if "none-space" as a command, if true, return, in order to prevent any spam in case, lower chance of getting kick heh.
            return
        bot.command_prefix = commands.when_mentioned_or(*cmd_prefix)
        if "help" in msg.content: #changing setting for help, if guild owner want Help command to be via PM or to guild.
            if await bot.db.redis.get("{}:Config:Whisper".format(msg.guild.id)) == "on":
                bot.dm_help =True
            else:
                bot.dm_help =False
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
    raw_cogs = list_cogs()
    for cogs in raw_cogs:
        try:
            bot.load_extension(cogs)
            print (f"Load {cogs}")
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
    try:
        # await bot.owner.send(f"```py\n{Current_Time}\nERROR!\n{error}```")
        await bot.error_channel.send(f"```py\n{Current_Time}\nERROR!\n{error}```")
    except:
        utils.prRed("Unable to send to owner/channel!")

if __name__ == '__main__':
    bot.run(utils.secret["nurevam_token"])
