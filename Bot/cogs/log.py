from discord.ext import commands
from PIL import Image
import datetime
import asyncio
import aiohttp
import io


class Log():
    def __init__(self,bot):
        self.bot = bot
        self.redis = bot.db.redis
        self.config = {}
        loop = asyncio.get_event_loop()
        loop.create_task(self.timer())

    def time(self):
        return datetime.datetime.now().strftime("%H:%M:%S")

    def format_msg(self,author):
        return "`[{}]`:__{} [{}]__ ".format(self.time(),author,author.id)

    async def avatar(self,before,after):
        with aiohttp.ClientSession() as sesson:
            try:
                async with sesson.get(before.avatar_url) as resp:
                        old = Image.open(io.BytesIO(await resp.read()))
            except:
                print("System failed! of Before")
                async with sesson.get(before.default_avatar_url) as resp:
                        old = Image.open(io.BytesIO(await resp.read()))
                        print(old.size)
                        old.thumbnail((128,128),Image.ANTIALIAS)
            try:
                async with sesson.get(after.avatar_url) as resp:
                    new = Image.open(io.BytesIO(await resp.read()))
            except:
                print("System failed! of after")
                async with sesson.get(after.default_avatar_url) as resp:
                    new = Image.open(io.BytesIO(await resp.read()))
                    print(new.size)
                    new.thumbnail((128,128),Image.ANTIALIAS)
        update = Image.new('RGB',(256,128))
        update.paste(old,(0,0))
        update.paste(new,(128,0))
        fp = io.BytesIO()
        update.save(fp,format='PNG')
        fp.seek(0)
        dest = self.bot.get_channel(self.config[after.server.id]["channel"])
        await self.bot.send_file(dest,fp,filename="Pic.png",content="{} **change avatar**".format(self.format_msg(after)))

    async def on_member_update(self,before,after):
        if self.config.get(after.server.id):
            msg_bool = False
            msg = self.format_msg(after)
            config = self.config[after.server.id]
            if before.name != after.name:
                if config.get("name"):
                    msg_bool = True
                    msg += "have changed username to **{}**".format(after.name)
            if before.nick != after.nick:
                if config.get("nickname"):
                    if after.nick is None:
                        msg += "remove nick".format(after.display_name)
                    else:
                        msg += "has changed nick from {} to {}".format(before.nick,after.nick)
                    msg_bool = True
            if before.avatar != after.avatar:
                if config.get("avatar"):
                    return await self.avatar(before,after)
            if msg_bool:
                await self.send(after.server.id,msg)

    async def on_message_edit(self,before,after):
        if after.channel.is_private:
            return
        if self.config.get(after.server.id):
            if self.config[after.server.id].get('edit'):
                if before.content != after.content:
                    msg = self.format_msg(after.author)
                    msg += "*have edit message in* {}: ".format(after.channel.mention)
                    msg += "```diff\n-{}\n+{}\n```".format(before.clean_content.replace("\n","\n-"),after.clean_content.replace("\n","\n+"))
                    await self.send(after.server.id,msg)

    async def on_message_delete(self,msg):
        if msg.channel.is_private:
            return
        if self.config.get(msg.server.id):
            if self.config[msg.server.id].get("delete"):
                message = self.format_msg(msg.author)
                if msg.attachments:
                    message += "*have delete attachments*"
                else:
                    message += "*have delete this message* in {}: ".format(msg.channel.mention)
                    message += "{}".format(msg.content)
                await self.send(msg.server.id,message)

    async def on_member_join(self,member):
        if self.config.get(member.server.id):
            if self.config[member.server.id].get("join"):
                msg = self.format_msg(member)
                msg += "have join server "
                await self.send(member.server.id,msg)

    async def on_member_remove(self,member):
        if self.config.get(member.server.id):
            if self.config[member.server.id].get("left"):
                msg = self.format_msg(member)
                msg += "have left server "
                await self.send(member.server.id,msg)

    async def send(self,server_id,msg):
        dest= self.bot.get_channel(self.config[server_id]["channel"])
        await self.bot.send_message(dest,msg)

    async def timer(self):
        while True:
            server_list = await self.redis.smembers("Info:Log")
            for x in server_list:
                config = await self.redis.hgetall("{}:Log:Config".format(x))
                self.config.update({x:config})
            self.bot.log_config = self.config
            await asyncio.sleep(60)

def setup(bot):
    bot.add_cog(Log(bot))