from discord.ext import commands
from .utils import utils
from PIL import Image
import datetime
import asyncio
import discord
import aiohttp
import logging
import io

log = logging.getLogger(__name__)

class Log():
    def __init__(self,bot):
        self.bot = bot
        self.redis = bot.db.redis
        self.config = {}
        self.bg = utils.Background("log",80,60,self.bg_event,log)
        self.bot.background.update({"log":self.bg})
        self.bg.start()

    def __unload(self):
        self.bg.stop()

    def time(self):
        return datetime.datetime.utcnow().strftime("%H:%M:%S")

    def format_msg(self,author):
        return "`[{0}]`:__{1} [{1.id}]__ ".format(self.time(),author)

    def format_embed(self,author,title = None):
        embed = discord.Embed(title = title)
        embed.set_author(name ="{} - [{}]".format(author,author.id),icon_url=author.avatar_url or author.default_avatar_url)
        embed.timestamp = datetime.datetime.utcnow()
        return embed

    async def avatar(self,before,after):
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(before.avatar_url) as resp:
                        old = Image.open(io.BytesIO(await resp.read()))
                        old.thumbnail((128,128),Image.ANTIALIAS)
            except:
                async with session.get(before.default_avatar_url) as resp:
                        old = Image.open(io.BytesIO(await resp.read()))
                        old.thumbnail((128,128),Image.ANTIALIAS)
            try:
                async with session.get(after.avatar_url) as resp:
                    new = Image.open(io.BytesIO(await resp.read()))
                    new.thumbnail((128,128),Image.ANTIALIAS)
            except:
                async with session.get(after.default_avatar_url) as resp:
                    new = Image.open(io.BytesIO(await resp.read()))
                    new.thumbnail((128,128),Image.ANTIALIAS)

        update = Image.new('RGB',(256,128))
        update.paste(old,(0,0))
        update.paste(new,(128,0))
        fp = io.BytesIO()
        update.save(fp,format='PNG')
        fp.seek(0)
        dest = self.bot.get_channel(int(self.config[after.guild.id]["channel"]))

        if dest is None:
            return log.debug("Channel is not found")
        try:
            await dest.send(file = discord.File(fp,filename="Pic.png"),content="{} **change avatar**".format(self.format_msg(after)))
        except discord.Forbidden:
            pass #if bot cannot attach picture, that mean it does not have perma and there nothing we can do about it.

    async def on_member_update(self,before,after):
        if self.config.get(after.guild.id):
            msg_bool = False
            msg = self.format_msg(after)
            config = self.config[after.guild.id]
            if before.name != after.name:
                if config.get("name"):
                    msg_bool = True
                    msg ="`[{0}]`:__{1} [{1.id}]__ ".format(self.time(), before)
                    msg += "has changed his or her username to **{}**".format(after.name)
            if before.nick != after.nick:
                if config.get("nickname"):
                    if after.nick is None:
                        msg += "removed his or her nick".format(after.display_name)
                    else:
                        msg += "has changed his or her nick from {} to {}".format(before.nick,after.nick)
                    msg_bool = True
            if before.avatar != after.avatar:
                if config.get("avatar"):
                    await self.avatar(before,after)
            if msg_bool:
                await self.send(after.guild.id,msg)

    async def on_message_edit(self,before,after):
        if isinstance(before.channel,discord.TextChannel):
            if self.config.get(after.guild.id):
                if self.config[after.guild.id].get('edit') and before.content != after.content:
                    if after.author.bot and self.config[after.guild.id].get("bot"):
                        return
                    before.content = u"\uFFFC" if bool(before.content) is False else before.content
                    # msg = self.format_msg(after.author)
                    msg = "{}".format(after.channel.mention)
                    embed = self.format_embed(after.author,"Edited")
                    embed.url = after.jump_url
                    embed.description = msg
                    embed.add_field(name = "Before",value = before.content,inline=False)
                    embed.add_field(name = "After",value = after.content,inline=False)
                    # msg += "```diff\n-{}\n+{}\n```".format(before.clean_content.replace("\n","\n-").replace("`","\`"),after.clean_content.replace("\n","\n+").replace("`","\`"))
                    await self.send(after.guild.id,embed)

    async def on_message_delete(self,msg):
        if isinstance(msg.channel,discord.DMChannel):
            return
        if msg.author.id == self.bot.user.id:
            return
        if self.config.get(msg.guild.id):
            if self.config[msg.guild.id].get("delete"):
                if msg.author.bot and self.config[msg.guild.id].get("bot"):
                        return

                message = self.format_msg(msg.author)
                if msg.attachments:
                    message += "*has deleted attachments*"
                else:
                    message += "*has deleted the following message* in {}: ".format(msg.channel.mention)
                    message += "{}".format(msg.clean_content)
                await self.send(msg.guild.id,message)

    async def on_member_join(self,member):
        if self.config.get(member.guild.id):
            if self.config[member.guild.id].get("join"):
                # msg = self.format_msg(member)

                # msg += "has joined the guild "
                embed = self.format_embed(member,"Join")
                age = datetime.datetime.utcnow() - member.created_at
                print(age.seconds)
                if age.seconds <= 600:
                    embed.colour = 0xdda453
                    embed.set_footer(text="Account created {0:.2f} mins ago".format(age.seconds/60))
                else:
                    embed.colour = 0x53dda4
                    if age.days >= 1:
                        embed.set_footer(text = "Account created {0} days ago".format(age.days))
                    else:
                        if age.seconds >= 3600:
                            x = "{} hours ago".format(int(age.seconds/3600)) #hours
                        else:
                            x = "{} mins ago".format(int(age.seconds/60)) #min
                        embed.set_footer(text = "Account created {} | {} members".format(x,member.guild.member_count))
                await self.send(member.guild.id,embed)
                # await self.send(member.guild.id,msg)

    async def on_member_remove(self,member):
        if self.config.get(member.guild.id):
            if self.config[member.guild.id].get("left"):
                embed = self.format_embed(member,"Left")
                age = datetime.datetime.utcnow() - member.joined_at
                embed.set_footer(text = "Was here since {} | {} member".format(age,member.guild.member_count))
                await self.send(member.guild.id,embed)

    async def send(self,guild_id,msg):
        channel_id = self.config[guild_id].get("channel")
        if channel_id is None:
            return log.debug("Channel is not found")
        dest = self.bot.get_channel(int(channel_id))
        try:
            if isinstance(msg,str):
                msg = msg.replace("@","@\u200b")
                await dest.send(msg)
            else:
                await dest.send(embed=msg)
        except:
            pass

    async def bg_event(self):
        guild_list = await self.redis.smembers("Info:Log")
        for x in guild_list:
            if await self.redis.hget("{}:Config:Cogs".format(x),"log") == "on":
                config = await self.redis.hgetall("{}:Log:Config".format(x))
                self.config.update({int(x):config})
                self.bot.log_config = self.config
        return

def setup(bot):
    bot.add_cog(Log(bot))
