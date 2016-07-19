from discord.ext import commands
import datetime
import asyncio

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
                    msg_bool = True
                    msg += "changed avatar from {} to {}".format(before.avatar_url,after.avatar_url)
            if msg_bool:
                await self.send(after.server.id,msg)

    async def on_message_edit(self,before,after):
        if self.config.get(after.server.id):
            if self.config[after.server.id].get('edit'):
                if before.content != after.content:
                    print("get ready")
                    msg = self.format_msg(after.author)
                    msg += "*have edit message in* {}: ".format(after.channel.mention)
                    msg += "```diff\n-{}\n+{}\n```".format(before.content,after.content)
                    await self.send(after.server.id,msg)

    async def on_message_delete(self,msg):
        if self.config.get(msg.server.id):
            if self.config[msg.server.id].get("delete"):
                message = self.format_msg(msg.author)
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

    async def send(self,id,msg):
        server_id = self.bot.get_channel(self.config[id]["channel"])
        await self.bot.send_message(server_id,msg)

    async def timer(self):
        while True:
            server_list = await self.redis.smembers("Info:Log")
            for x in server_list:
                config = await self.redis.hgetall("{}:Log:Config".format(x))
                self.config.update({x:config})
            await asyncio.sleep(60)

def setup(bot):
    bot.add_cog(Log(bot))