from difflib import SequenceMatcher
from discord.ext import commands
from .utils import utils
import datetime
import asyncio
import discord
import logging

log = logging.getLogger(__name__)

class Mode_config:
    invite = "invite_link"
    link = "any_link"
    spam = "spam_msg"
    member_age = "member_age"
    multi_people = "multi_people"
    multi_ping = "multi_ping"

class AntiRaid():
    """
    A mod tool for Mods.
    """
    def __init__(self, bot):
        self.bot = bot
        self.redis = bot.db.redis
        self.bot.say_edit = bot.say
        self.config = {}
        self.bg = utils.Background("anti raid",60,30,self.bg_event,log)
        self.bot.background.update({"anti raid":self.bg})
        self.bg.start()


    def __unload(self):
        self.bg.stop()

    async def bg_event(self):
        guild_list = await self.redis.smembers("Info:AntiRaid")
        for x in guild_list:
            if await self.redis.hget("{}:Config:Cogs".format(x),"antiraid") == "on":
                config = await self.redis.hgetall("{}:AntiRaid:Config".format(x))
                self.config.update({int(x):config})

    def get_config(self,guild,config):
        return self.config.get(guild,{}).get(config,None)

    async def security_level(self,member,mode,reason):
        #get level of mode
        #there will be 5 level
        #0 is nothing
        #1 is warning user
        #2 is role grant
        #3 is kick
        #4 is softban
        #5 is ban
        level = int(self.get_config(member.guild.id,mode) or "0")

        try:
            if level == 4 or level == 5:
                await member.ban(reason = reason)
                if level == 4:
                    await member.unban(reason = reason)
            elif level == 3:
                await member.kick(reason = reason)
            elif level == 2:
                #get role here
                role_id = await self.redis.smembers('{}:AntiRaid:mute_roles'.format(member.guild.id))
                role = [x for x in member.guild.roles if str(x.id) in role_id]
                if role is None: return
                await member.add_roles(*role,reason = reason)
            elif level == 1:
                #warn user
                pass
            else:
                pass
        except Exception as e: #no perm? oh well
            utils.prRed("Error from anti raid security level \n\n{}".format(e))
            pass

    async def check_discord_invite_link(self,msg):
        if "discord.gg/" in msg.content:
            if self.get_config(msg.guild.id,"invite_link"):
                list_invite = await msg.guild.invites()
                if len([x for x in list_invite if x.code in msg.content]) is 0:
                    await self.security_level(msg.author,Mode_config.invite,"Invite Link not from this server. -AntiRaid")
                    await msg.channel.send("Invite link are not allowed!")
                    try:
                        await msg.delete()
                    except:
                        pass

    async def check_any_link(self,msg):
        if ("http" in msg.content or "www." in msg.content) and self.get_config(msg.guild.id,"any_link") != "0":
            created = msg.author.joined_at
            current = datetime.datetime.utcnow()
            age = current - created
            if age.total_seconds() <= int(self.get_config(msg.guild.id,"any_link_time")):
                await self.security_level(msg.author,Mode_config.link,"Any link are not allow within few min of member join")
                try:
                    await msg.delete()
                except:
                    pass

    async def check_massive_ping(self,msg):
        if self.get_config(msg.guild.id,Mode_config.multi_ping):
            if len(msg.mentions) >= int(self.get_config(msg.guild.id,"multi_ping_limit")):
                await self.security_level(msg.author,Mode_config.multi_ping,"User did massive ping")
                try:
                    await msg.delete()
                except:
                    pass

    async def check_spamming_msg(self,msg):
        await self.redis.sadd("{0.guild.id}:AntiRaid:spamming_msg:{0.author.id}".format(msg),msg.content)
        count = await self.redis.incr("{0.guild.id}:AntiRaid:spamming:counting:{0.author.id}".format(msg))
        if await self.redis.ttl("{0.guild.id}:AntiRaid:spamming:counting:{0.author.id}".format(msg)) == -1:
            await self.redis.expire("{0.guild.id}:AntiRaid:spamming_msg:{0.author.id}".format(msg),int(self.get_config(msg.guild.id,"spam_msg_time")))
            await self.redis.expire("{0.guild.id}:AntiRaid:spamming:counting:{0.author.id}".format(msg),int(self.get_config(msg.guild.id,"spam_msg_time")))

        if int(count) >= int(self.get_config(msg.guild.id,"spam_msg_count")):
            msg_count = await self.redis.scard("{0.guild.id}:AntiRaid:spamming_msg:{0.author.id}".format(msg))
            if  msg_count == 1 and msg_count != count and count != 1: #if user is spamming same message within time.
                await self.security_level(msg.author,Mode_config.spam,"This user has been spamming message")
            # else:
            #     print("under else")
            #     msg_list = await self.redis.smembers("{0.guild.id}:AntiRaid:spamming_msg:{0.author.id}".format(msg))
            #     utils.prGreen(msg_list)
            #     counter = 0
                # precent = int(self.get_config(msg.guild.id,"spam_msg_percent")) / 100 # getting 0.xxxx
                # for i in range(0,len(msg_list)):
                #     for j in range(i+1,len(msg_list)):
                #         r = SequenceMatcher(None, msg_list[i],msg_list[j]).ratio()
                #         print(r)
                #         if r >= precent:
                #             counter += 1
                # utils.prPurple(counter)
                # if counter == count:
                #     print("counter == count")
                #     await self.security_level(msg.author,Mode_config.spam,"This user has been spamming message")

    async def check_account_age(self,member):
        if self.get_config(member.guild.id,"member_age") != "0":
            created = member.created_at
            current = datetime.datetime.utcnow()
            age = current - created
            if int(age.total_seconds()) <= int(self.get_config(member.guild.id,"member_age_time")):
                await self.security_level(member,Mode_config.member_age,reason = "Account is under requirement,as it is {} second old".format(age.total_seconds()))

    async def check_multi_people_join(self,member):
        guild = member.guild
        # checking if multi people joining server at once
        if self.get_config(guild.id, "multi_people") != "0":
            await self.redis.sadd("{}:AntiRaid:multi_ppl".format(guild.id), member.id)
            # checking if it already set expire, if not which is -1, set it
            if self.redis.ttl("{}:AntiRaid:multi_ppl".format(guild.id)) == -1:
                await self.redis.expire("{}:AntiRaid:multi_ppl".format(guild.id),int(self.get_config(guild.id, "multi_people_time")))
            # now checking how many join in during that time
            if self.redis.scard("{}:AntiRaid:multi_ppl".format(guild.id)) >= int(self.get_config(guild.id, "multi_people_limit")):
                    raw_member_list = await self.redis.smembers("{}:AntiRaid:multi_ppl".format(guild.id))
                    member_list = [guild.get_member(x) for x in raw_member_list]
                    for mem in member_list:
                        if mem is None: continue
                        try:
                            await self.security_level(mem,Mode_config.multi_people,"Multi people joining at once.")
                        except Exception as e:
                            utils.prRed("Something wrong with check_multi_people_join function, error:{}".format(e))
                            continue
                    await self.redis.delete("{}:AntiRaid:multi_ppl".format(guild.id)) #if there is still more to come after this.


    async def on_message(self,msg):
        if msg.author.id == self.bot.user.id or isinstance(msg.channel,discord.DMChannel):
            return
        if self.config.get(msg.guild.id,False): #can be any as long as we know config exit
            await self.check_massive_ping(msg)

            #checking invite link and delete it if it not allow.
            await self.check_discord_invite_link(msg)
            await self.check_any_link(msg)

            # checking if person spamming
            await self.check_spamming_msg(msg)

    async def on_member_join(self,member):
        await self.check_account_age(member)
        await self.check_multi_people_join(member)


def setup(bot):
    bot.add_cog(AntiRaid(bot))