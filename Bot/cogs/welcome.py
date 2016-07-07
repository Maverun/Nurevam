from .utils import utils
import traceback
import datetime
import asyncio
import discord

class Welcome(): #Allow to welcome new members who join server. If it enable, will send them a message.
    def __init__(self,bot):
        self.bot = bot
        self.redis = bot.db.redis

    async def on_member_join(self,member):
        if await self.redis.hget("{}:Config:Cogs".format(member.server.id),"welcome") == "on":
            config = await self.redis.hgetall("{}:Welcome:Message".format(member.server.id))
            try:
                if config["whisper"] == "on":
                    msg = await self.bot.send_message(member,config["message"].format(user=member.name,server=member.server,user_mention=member.mention))
                else:
                    msg =await self.bot.send_message(self.bot.get_channel(config["channel"]),config["message"].format(user=member.name,server=member.server,user_mention=member.mention))
                if await self.redis.hget("{}:Welcome:Message".format(member.server.id),"delete_msg"):
                    await asyncio.sleep(int(config["delete_msg"]))
                    await self.bot.delete_message(msg)
            except Exception as e:
                await self.bot.send_message(member.server.owner,"There is error with newcomer, please report to creator about this.\n {}".format(e))
                Current_Time = datetime.datetime.utcnow().strftime("%b/%d/%Y %H:%M:%S UTC")
                utils.prRed(Current_Time)
                utils.prRed("Error!")
                utils.prRed(traceback.format_exc())
                error =  '```py\n{}\n```'.format(traceback.format_exc())
                await self.bot.send_message(self.bot.get_channel("123934679618289669"), "```py\n{}```".format(Current_Time + "\n"+ "ERROR!") + "\n" +  error)

        #Now assign a roles.
            if config.get("role") == "on":
                try:
                    role_list = await self.redis.smembers('{}:Welcome:Assign_Roles'.format(member.server.id))
                    role_obj=[]
                    for x in role_list:
                        role_obj.append(discord.utils.get(member.server.roles,id=x))
                    await self.bot.add_roles(member,*role_obj)
                except Exception as e:
                    await self.bot.send_message(member.server.owner,"There is error with newcomer with roles related, please report to creator about this.\n {}".format(e))
                    Current_Time = datetime.datetime.utcnow().strftime("%b/%d/%Y %H:%M:%S UTC")
                    utils.prRed(Current_Time)
                    utils.prRed("Error!")
                    utils.prRed(traceback.format_exc())
                    error =  '```py\n{}\n```'.format(traceback.format_exc())
                    await self.bot.send_message(self.bot.get_channel("123934679618289669"), "```py\n{}```".format(Current_Time + "\n"+ "ERROR!") + "\n" +  error)

def setup(bot):
    bot.add_cog(Welcome(bot))