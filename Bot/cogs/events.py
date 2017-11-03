from discord import errors as discord_error
from prettytable import PrettyTable
from discord.ext import commands
from .utils import utils
import traceback
import datetime
import logging
import discord

class Events:
    def __init__(self,bot):
        self.bot = bot
        self.redis = bot.db.redis
        self.error_log = False
        self.debug_cog = {}

    def Time(self):
        return datetime.datetime.now().strftime("%b/%d/%Y %H:%M:%S")

#############################################################
#    _        _         _                                   #
#   | |      (_)       | |                                  #
#   | |       _   ___  | |_    ___   _ __     ___   _ __    #
#   | |      | | / __| | __|  / _ \ | '_ \   / _ \ | '__|   #
#   | |____  | | \__ \ | |_  |  __/ | | | | |  __/ | |      #
#   |______| |_| |___/  \__|  \___| |_| |_|  \___| |_|      #
#                                                           #
#############################################################

    async def on_guild_join(self,guild): #IF Bot join guild, it will add to record of those.
        print ("\033[96m<EVENT JOIN>: \033[94m {} :({}) -- {}\033[00m".format(self.Time(), guild.id, guild.name))
        utils.prGreen("\t\t Servers: {}\t\t Members: {}".format(len(self.bot.guilds), len(self.bot.users)))
        await self.redis.hset("Info:Server",str(guild.id),str(guild.name))
        await self.redis.set("Info:Total Server",len(self.bot.guilds))
        await self.redis.set("Info:Total Member",len(self.bot.users))
        if self.redis.exists("{}:Config:Cogs".format(guild.id)): # if it exist, and going to be expire soon, best to persists them, so they don't lost data
            async for key in self.redis.iscan(match="{}*".format(guild.id)):
                await self.redis.persist(key)
        else:
            await self.redis.set("{}:Config:CMD_Prefix".format(guild.id),"!")
        #Server setting
        await self.redis.hset("{}:Config:Delete_MSG".format(guild.id),"core","off") #just in case

    async def on_guild_remove(self,guild): #IF bot left or no longer in that guild. It will remove this
        print("\033[91m<EVENT LEFT>:\033[94m[ {} : \033[96m({})\033[92m -- {}\033[00m".format(self.Time(), guild.id, guild.name))
        utils.prGreen("\t\t Severs:{}\t\tMembers:{}".format(len(self.bot.guilds), len(self.bot.users)))
        await self.redis.hdel("Info:Server",guild.id)
        age = datetime.datetime.utcnow() - guild.me.joined_at if guild.me is not None else None #return None instead of giving error chuck not update?
        #Set all database to expire, will expire in 30 days, so This way, it can save some space,it would unto when it is back to that guild and setting changed.
        count = 0
        async for key in self.redis.iscan(match="{}*".format(guild.id)):
            await self.redis.expire(key,1209600)
            count += 1
        if age is not None:
            utils.prGreen("{0.days} day, {0.seconds} seconds".format(age))
        utils.prGreen("Set {} expire".format(count))

    async def on_guild_update(self,before,after): #If guild update name and w/e, just in case, Update those
        print("\033[95m<EVENT Update>:\033[94m {} :\033[96m {} \033[93m | \033[92m({}) -- {}\033[00m".format(self.Time(),after.name,after.id, after))
        if after.icon:
            await self.redis.set("{}:Icon".format(after.id),after.icon)
        await self.redis.hset("Info:Server",after.id,after.name)

    async def on_member_join(self,member):
        print("\033[98m<Event Member Join>:\033[94m {} :\033[96m {} ||| \033[93m ({})\033[92m  -- {} ||| {}\033[00m".format(self.Time(), member.guild.name, member.guild.id, member.name, member.id))
        await self.redis.set("Info:Total Member",len(set(self.bot.get_all_members())))

    async def on_member_remove(self,member):
        print("\033[93m<Event Member Left>:\033[94m {}:\033[96m {} ||| \033[93m ({})\033[92m -- {} ||| {}\033[00m".format(self.Time(), member.guild.name, member.guild.id, member.name, member.id))
        await self.redis.set("Info:Total Member",len(set(self.bot.get_all_members())))

    async def on_member_update(self,before,after):
        check = await self.redis.get("Member_Update:{}:check".format(after.id))
        if check: #If it true, return, it haven't cool down yet
            return
        if before.avatar != after.avatar:
            if after.avatar is None:
                return
            print("\033[97m<Event Member Update Avatar>:\033[94m {} :\033[92m {} ||| {}\033[00m".format(self.Time(), after.name, after.id))
            await self.redis.hset("Info:Icon",after.id,after.avatar)
        if before.name != after.name:
            print("\033[97m<Event Member Update Name>: \033[94m {}:\033[93m Before : {} |||\033[92m After : {} ||| {}\033[00m".format(self.Time(),before.name,after.name, after.id))
            await self.redis.hset("Info:Name",after.id,str(after))
        await self.redis.set("Member_Update:{}:check".format(after.id),'cooldown',expire=15) #To stop multi update

    async def on_command(self,ctx):
        if isinstance(ctx.message.channel,discord.DMChannel):
            return
        print("\033[96m<Event Command>\033[94m {0}:\033[96m {1.guild.name} ||| \033[93m {1.author} ||| \033[94m ({1.author.id})\033[92m ||| {1.clean_content}\033[00m".format(self.Time(), ctx.message))

    async def on_message(self,msg):
            if self.bot.user.id == msg.author.id:
                if isinstance(msg.channel,discord.DMChannel) is False:
                    try:
                        if self.bot.log_config.get(msg.guild.id):
                            if str(msg.channel.id) in self.bot.log_config[msg.guild.id]['channel']:
                                return
                    except:
                        pass
                if isinstance(msg.channel,discord.TextChannel) is False:
                    utils.prCyan("PRIVATE")
                    utils.prGreen("<Event Send> {} : {} |||{}".format(self.Time(), msg.author.name, msg.clean_content))
                else:
                    try:
                        if msg.embeds:
                            table = PrettyTable() #best to use it i guess
                            data = msg.embeds[0].fields
                            if data:
                                for x in data:
                                    table.add_column(x.name,x.value.split("\n"))
                            content = str(msg.embeds[0].description) +"\n"
                            content +="\n" + str(table)
                        else:
                            content = msg.clean_content
                        utils.prGreen("<Event Send> {} : {} ||| {} ||| ({}) ||| {}".format(self.Time(), msg.author.name,msg.guild.name,msg.guild.id, content))
                    except:
                        utils.prGreen("<Event Send> {} : {} ||| {} ||| ({}) ||| {}".format(self.Time(), msg.author.name,msg.guild.name,msg.guild.id,msg.embeds))

    async def on_command_completion(self,ctx):
        if ctx.command.cog_name is None or isinstance(ctx.message.channel,discord.DMChannel):
            return
        try:
            print(ctx.command.cog_name)
            check = await self.bot.db.redis.hgetall("{}:Config:Delete_MSG".format(ctx.message.guild.id))
            if check.get(ctx.command.cog_name.lower()) == "on":
                await ctx.message.delete()
            await self.redis.hincrby("{0.guild.id}:Total_Command:{0.author.id}".format(ctx.message),ctx.invoked_with, increment=1)
            await self.redis.hincrby("Info:Total_Command", ctx.invoked_with, increment=1)
            await self.redis.hincrby("{0.guild.id}:Total_Command:User:{0.author.id}".format(ctx.message),ctx.invoked_with, increment=1)
        except:
            utils.prRed("Failed to delete user command - {0.name}  - {0.id}\n".format(ctx.message.guild))
            utils.prRed(traceback.format_exc())

    async def send_cmd_help(self,ctx):
        if ctx.invoked_subcommand:
            pages = await self.bot.formatter.format_help_for(ctx,ctx.invoked_subcommand)
            print(pages)
            for page in pages:
                await ctx.send(page.replace("\n","fix\n",1))
        else:
            pages = await self.bot.formatter.format_help_for(ctx,ctx.command)
            for page in pages:
                await ctx.send(page.replace("\n","fix\n",1))

    async def on_command_error(self,ctx,error):
        if self.bot.user.id == 181503794532581376 or self.error_log:
            print(error)
        if isinstance(error, commands.MissingRequiredArgument):
            await self.send_cmd_help(ctx)
        elif isinstance(error,commands.BadArgument):
            await self.send_cmd_help(ctx)
        elif isinstance(error, commands.CommandInvokeError):
            if isinstance(error.original,discord_error.Forbidden):
                await ctx.send("I am sorry, I need a certain permission to run it...")
                traceback.print_exception(type(error), error, error.__traceback__)
                return utils.prRed(type(error.original))
            errors = traceback.format_exception(type(error), error, error.__traceback__)
            Current_Time = datetime.datetime.utcnow().strftime("%b/%d/%Y %H:%M:%S UTC")
            utils.prRed(Current_Time)
            utils.prRed("Error!")
            traceback.print_exception(type(error), error, error.__traceback__)
            cog_error =  '```fix\nCogs:{0.command.cog_name}\tCommand:{0.command}\tAuthor:{0.message.author}-{0.message.author.id}\n' \
                         'Server:{0.message.guild.id}\n{0.message.clean_content}\nError:\n{1}```'.format(ctx,error)
            msg ="```py\n{}```\n{}\n```py\n{}\n```".format(Current_Time + "\n"+ "ERROR!",cog_error,"".join(errors).replace("`",""))
            if len(msg) >= 1900:
                msg = await utils.send_hastebin(msg)
            await self.bot.owner.send(msg)
            await ctx.send("You either used the command incorrectly or an unexpected error occurred. A report has been sent to the creator so you can hope for a fix soon.")

    @commands.command(hidden = True)
    @commands.check(utils.is_owner)
    async def set_error(self,ctx,cog=None):
        """
        On a prod guild, it can get very spamming, so I would set it for just in case...
        """
        if cog:
            check = self.debug_cog.get(cog)
            if check or check is False:
                log = logging.getLogger("cogs.{}".format(cog))
                if check == True:
                    log.setLevel(logging.INFO)
                    utils.prPurple("Getting info to paste into hastebin")
                    with open("bot_log.txt","r+") as f:
                        msg = await utils.send_hastebin(f.read())
                        await ctx.send(content = msg)
                else:
                    log.setLevel(logging.DEBUG)
                self.debug_cog[cog] = not(check)
                await ctx.send("Set to {}".format(not(check)))
            else:
                log = logging.getLogger("cogs.{}".format(cog ))
                log.setLevel(logging.DEBUG)
                format_log = logging.Formatter('%(asctime)s:\t%(levelname)s:\t%(name)s:\tFunction:%(funcName)s ||| MSG: %(message)s')
                console = logging.StreamHandler()
                console.setFormatter(format_log)
                handler = logging.FileHandler(filename='bot_log.txt', encoding='utf-8', mode='w')
                handler.setFormatter(format_log)
                log.addHandler(console)
                log.addHandler(handler)
                self.debug_cog[cog] = True
                await ctx.send("Set to True")
        else:
            self.error_log = not (self.error_log)
            await ctx.send("Set {}".format(self.error_log))


def setup(bot):
    bot.add_cog(Events(bot))
