from .utils import utils
import datetime
import traceback

class Events():
    def __init__(self,bot):
        self.bot = bot
        self.redis = bot.db.redis

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

    async def on_server_join(self,server): #IF Bot join server, it will add to record of those.
        print ("\033[92m<EVENT JOIN>: \033[94m {} :({}) -- {}\033[00m".format(self.Time(), server.id, server.name))
        utils.prGreen("\t\t Servers: {}\t\t Members: {}".format(len(self.bot.servers), len(set(self.bot.get_all_members()))))
        await self.redis.hset("Info:Server",str(server.id),str(server.name))
        await self.redis.set("Info:Total Server",len(self.bot.servers))
        await self.redis.set("Info:Total Member",len(set(self.bot.get_all_members())))
        await self.redis.set("{}:Config:CMD_Prefix".format(server.id),"!")

        #Server setting
        await self.redis.hset("{}:Config:Delete_MSG".format(server.id),"core","off")

    async def on_server_remove(self,server): #IF bot left or no longer in that server. It will remove this
        print("\033[91m<EVENT LEFT>:\033[94m[ {} : \033[96m({})\033[92m -- {}\033[00m".format(self.Time(), str(server.id), str(server.name)))
        utils.prGreen("\t\t Severs:{}\t\tMembers:{}".format(len(self.bot.servers), len(set(self.bot.get_all_members()))))
        await self.redis.hdel("Info:Server",server.id)

    async def on_server_update(self,before,after): #If server update name and w/e, just in case, Update those
        print("\033[95m<EVENT Update>:\033[94m {} :\033[96m {} \033[93m | \033[92m({}) -- {}\033[00m".format(self.Time(),after.name,after.id, after))
        if after.icon:
            await self.redis.set("{}:Icon".format(after.id),after.icon)
        await self.redis.hset("Info:Server",str(after.id),str(after))

    async def on_member_join(self,member):
        print("\033[98m<Event Member Join>:\033[94m {} :\033[96m {} ||| \033[93m ({})\033[92m  -- {} ||| {}\033[00m".format(self.Time(), member.server.name, member.server.id, member.name, member.id))
        await self.redis.set("Info:Total Member",len(set(self.bot.get_all_members())))

    async def on_member_remove(self,member):
        print("\033[93m<Event Member Left>:\033[94m {}:\033[96m {} ||| \033[93m ({})\033[92m -- {} ||| {}\033[00m".format(self.Time(), member.server.name, member.server.id, member.name, member.id))
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
            await self.redis.hset("Info:Name",after.id,after.name)
            await self.redis.set("Member_Update:{}:check".format(after.id),'cooldown',expire=10) #To stop multi update

    async def on_command(self,command,ctx):
        if ctx.message.channel.is_private:
            return
        print("\033[96m<Event Command>\033[94m {}:\033[96m {} ||| \033[93m {} ||| \033[94m ({})\033[92m ||| {}\033[00m".format(self.Time(),ctx.message.server.name, ctx.message.author.name, ctx.message.author.id, ctx.message.clean_content))
        await self.redis.hincrby("{}:Total_Command:{}".format(ctx.message.server.id,ctx.message.author.id),ctx.invoked_with,increment=1)
        await self.redis.hincrby("Info:Total_Command",ctx.invoked_with,increment=1)
        await self.redis.hincrby("{}:Total_Command:User:{}".format(ctx.message.server.id,ctx.message.author.id),ctx.invoked_with,increment=1)

    async def on_message(self,msg):
            if self.bot.user.id == msg.author.id:
                utils.prGreen("<Event Send> {} : {} ||| ({}) ||| {}".format(self.Time(), msg.author.name, msg.author.id, msg.clean_content))

    async def on_command_completion(self,command,ctx):
        try:
            check = await self.bot.db.redis.hgetall("{}:Config:Delete_MSG".format(ctx.message.server.id))
            if len(check)>0:
                if check.get(command.cog_name.lower(),None) == "on":
                    await self.bot.delete_message(ctx.message)
        except:
            utils.prRed("Failed to delete user command - {}  - {}\n".format(ctx.message.server.name,ctx.message.server.id))
            utils.prRed(traceback.format_exc())


def setup(bot):
    bot.add_cog(Events(bot))