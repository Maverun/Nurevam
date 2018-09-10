from .utils import utils
import traceback
import datetime
import discord

class Welcome(): #Allow to welcome new members who join guild. If it enable, will send them a message.
    def __init__(self,bot):
        self.bot = bot
        self.redis = bot.db.redis

    async def error(self,owner,e):
        # await owner.send("There is an error with a newcomer, please report this to the creator.\n {}".format(e))
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
                    msg = config["message"].format(user=member.name,server=member.guild,user_mention=member.mention)
                    if config.get("enable_delete") == "on":
                            time = int(config["delete_msg"])
                    else:
                        time = None

                    if config.get("whisper") == "on":
                         await member.send(msg,delete_after = time)
                    else:
                        await self.bot.get_channel(int(config["channel"])).send(msg,delete_after = time)

                #Now assign a roles.
                if config.get("role") == "on":
                    role_list = await self.redis.smembers('{}:Welcome:Assign_Roles'.format(member.guild.id))
                    role_obj=[]
                    for x in role_list:
                        if x == '': #if it return empty string
                            continue
                        role_obj.append(discord.utils.get(member.guild.roles,id=int(x)))
                    try:
                        await member.add_roles(*role_obj)
                    except discord.Forbidden:
                        pass #if unable to add user

            except Exception as e:
                await self.error(member.guild.owner, e)

def setup(bot):
    bot.add_cog(Welcome(bot))
