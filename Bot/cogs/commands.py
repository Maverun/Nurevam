from urllib.parse import urlparse
from discord.ext import commands
from .utils import utils
import collections
import traceback
import functools
import discord
import inspect
import logging
import asyncio
import datetime

log = logging.getLogger(__name__)

"""
Credit to Danny(Rapptz) for example of custom commands
It was based of his and improve from there with a lot of changes to my like.
I believe this cogs is full of hack.
"""


class CreateCustom:
    def __init__(self,**kwargs):
        self.name = kwargs.get('name')
        self.content = kwargs.get('content')
        self.brief= kwargs.get('brief')
        self.guild_id= kwargs.get('guild_id')


async def run_command(cmd,o,ctx,*args:str):
    """
    Custom Command
    """

    """
    Args:
        cmd: CreateCustom Obj
        o: Nothing
        ctx: ctx
        *args: any remain message from user
    """
    args = list(args)
    #ignore obj

    if(bool(urlparse(cmd.content).netloc)):
        temp = cmd.content.find(".", int(len(cmd.content)/2))
        temp = cmd.content[temp:]
        picture = False
        for x in ["png","gif","jpg","bmp","jpeg"]:
            if x in temp.lower():
                picture = True
                break
        if picture:
            embed = discord.Embed()
            embed.set_image(url = cmd.content)
            return await ctx.send(embed = embed)
    msg = ctx.message
    name = ""
    mention = ""
    #a bad way to fix it, way i know, sorry.
    cmd.content = cmd.content.replace("\\t","\t").replace("\\n","\n")
    if msg.mentions: #putting mention in
        ment = msg.mentions
        for i in range(len(ment)):
            x = ment.pop(0)
            blank = " "
            if len(ment) >1:
                blank = ","
            name += x.name + blank
            mention += x.mention + blank
            if args:
                log.debug("Cleaning out mentions")
                try:
                    for l in range(len(args)):
                        args.pop(args.index(x.mention)) #when there is dupe mention
                except Exception as e:
                    log.debug(e)
                    pass
    content = cmd.content.format(cmduser = msg.author.name,cmdmention = msg.author.mention,
                                 user = name, mention = mention,msg = " ".join(args))
    await ctx.send(content[:2000]) #sorry folk, you wont make it past 2k!

class CustomCmd(commands.Command):
    def __init__(self,func,**kwargs):
        self._entries = {}
        self.module = None
        super().__init__(func,**kwargs)
        self.name = kwargs.get("name",self.name)
        self.brief = kwargs.get("brief",self.brief)
        self.params = collections.OrderedDict()
        self.params["cog"] = self.cog # These are for help command to ignore errors by user.
        self.params["ctx"] = "nothing"# These are for help command to ignore errors by user.

    async def callback(self):
        pass #ignore any problem and JUST CARRY ON.

    async def invoke(self, ctx):
        server = ctx.message.guild
        if server is not None:
            log.debug("Invoke command: {} , guild ID {}".format(ctx.command.name,server.id))
            entry = self._entries.get(server.id)
            if entry is None:
                return
            
            # update the callback called
            self.callback = functools.partial(run_command, entry)
            self.params = inspect.signature(self.callback).parameters

        await super().invoke(ctx)


    async def can_run(self,ctx):
        server = ctx.message.guild
        if server is not None:
            log.debug("checking conditions, {} , {}".format(ctx.command.name,server.id))
            get_entry = self._entries.get(server.id)
            if get_entry: #to make brief for that server, totally hacky way?
                try:
                    ctx.bot.get_command(get_entry.name).brief = get_entry.brief or ""
                except: #if user didn't enter brief in.
                    pass
            return bool(get_entry)


class Custom_Commands(commands.Cog, name = "Custom Commands"):
    """
    An unique custom commands for your server!
    """
    def __init__(self,bot):
        self.bot = bot
        self.redis = bot.db.redis
        self.starter = True
        self.bg = utils.Background("customcmd",60,50,self.timer,log)
        self.bot.background.update({"customcmd":self.bg})
        self.bg.start()

    def cog_unload(self):
        self.bg.stop()

    def cog_check(self,ctx):
        return utils.is_enable(ctx,"custom commands")

    async def timer(self):
        try:
            for guild in list(self.bot.guilds):
                log.debug(guild)
                if await self.redis.hget("{}:Config:Cogs".format(guild.id),"custom commands") == "on":
                    list_name = await self.redis.smembers("{}:Customcmd:update_delete".format(guild.id))
                    log.debug(list_name)
                    if list_name:
                        for name in list_name: #if it edit or delete, either way remove them, we will do fresh update
                            cmd = self.bot.get_command(name)
                            print(cmd)
                            if cmd:
                                #Set None.. for some reason doesn't exist?
                                cmd._entries.pop(guild.id,None)
                        await self.redis.delete("{}:Customcmd:update_delete".format(guild.id))
                    if await self.redis.get("{}:Customcmd:update".format(guild.id)) or list_name or self.starter is True: #Which mean there is update
                        log.debug("adding commands")
                        cmd_content = await self.redis.hgetall("{}:Customcmd:content".format(guild.id))
                        cmd_brief = await self.redis.hgetall("{}:Customcmd:brief".format(guild.id))
                        log.debug("commands contents: {}".format(cmd_content))
                        for name,content in cmd_content.items():
                            log.debug("name {} : content: {}".format(name,content))
                            brief = cmd_brief[name]
                            entry = CreateCustom(name=name.lower(), content=content, brief = brief,guild_id=guild.id)
                            self.create_command(entry)
                        await self.redis.delete("{}:Customcmd:update".format(guild.id))
            self.starter = False

        except asyncio.CancelledError:
            return utils.prRed("Asyncio Cancelled Error")
        except Exception as e:
            utils.prRed(e)
            utils.prRed(traceback.format_exc())

    def create_command(self,cmd):
        cmd_exit = self.bot.get_command(cmd.name)
        log.debug(cmd_exit)
        if cmd_exit is None: #checking if we have exist command
            command = self.bot.command(name = cmd.name, brief = cmd.brief,cls = CustomCmd)(run_command) #Decorator
            command.cog = self #adding cog to command so it can format in help.
            command._entries[cmd.guild_id] = cmd
        elif isinstance(cmd_exit,CustomCmd):
            log.debug("command already exist")
            cmd_exit._entries[cmd.guild_id] = cmd

def setup(bot):
    bot.add_cog(Custom_Commands(bot))
