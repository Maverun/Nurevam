from .utils import utils
import traceback
import datetime
import asyncio
import discord

class Welcome(): #Allow to welcome new members who join guild. If it enable, will send them a message.
    def __init__(self,bot):
        self.bot = bot
        self.redis = bot.db.redis

    async def error(self,owner,e):
        await owner.send("There is an error with a newcomer, please report this to the creator.\n {}".format(e))
        Current_Time = datetime.datetime.utcnow().strftime("%b/%d/%Y %H:%M:%S UTC")
        utils.prRed(Current_Time)
        utils.prRed("Error!")
        utils.prRed(traceback.format_exc())
        error = '```py\n{}\n```'.format(traceback.format_exc())
        await self.bot.owner.send("```py\n{}```".format(Current_Time + "\n" + "ERROR!") + "\n" + error)

    async def on_member_join(self,member):
        if await self.redis.hget("{}:Config:Cogs".format(member.guild.id),"welcome") == "on":
            config = await self.redis.hgetall("{}:Welcome:Message".format(member.guild.id))
            try:
                if config.get("enable_message") == "on":
                    if config.get("whisper") == "on":
                        msg = member.send(config["message"].format(user=member.name,guild=member.guild,user_mention=member.mention))
                    else:
                        msg = self.bot.get_channel(int(config["channel"])).send(config["message"].format(user=member.name,server=member.guild,user_mention=member.mention))
                    if config.get("enable_delete") == "on":
                            await asyncio.sleep(int(config["delete_msg"]))
                            await msg.delete()
            except Exception as e:
                await self.error(member.guild.owner,e)

            #Now assign a roles.
            if config.get("role") == "on":
                try:
                    role_list = await self.redis.smembers('{}:Welcome:Assign_Roles'.format(member.guild.id))
                    role_obj=[]
                    for x in role_list:
                        role_obj.append(discord.utils.get(member.guild.roles,id=int(x)))
                    await member.add_roles(*role_obj)
                except Exception as e:
                    await self.error(member.guild.owner, e)

def setup(bot):
    bot.add_cog(Welcome(bot))
