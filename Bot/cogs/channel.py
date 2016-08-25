from discord.ext import commands
from .utils import utils
import discord
import asyncio


def check_roles(msg):
    Admin = utils.check_roles(msg, "Channel", "admin_roles")
    Normal= utils.check_roles(msg, "Channel", "user_roles")
    if Admin is True or Normal is True:
        return True
    else:
        return False

def is_enable(msg): #Checking if cogs' config for this server is off or not
    return utils.is_enable(msg, "channel")

class Channel():
    """
    Allow user create a temp channel within time limit
    """
    def __init__(self,bot):
        self.bot = bot
        self.redis=bot.db.redis
        self.bot.say_edit = bot.says_edit
        self.Temp_Chan={} #Making a Dict so it can track of channel in
        self.Temp_Count=0 #To count how many channel for limit
        self.everyone = discord.PermissionOverwrite(read_messages=False)
        self.admin =  discord.PermissionOverwrite(read_messages=True)
        self.allow=discord.Permissions.none()
        self.allow.read_messages=True
        self.bot.add_listener(self.channel_status,"on_channel_delete")

    async def channel_status(self,name):
        if self.Temp_Chan.get(name.name):
            self.Temp_Chan.pop(name.name)
            self.Temp_Count -=1

    @commands.check(is_enable)
    @commands.check(check_roles)
    @commands.group("channel",brief="Main command of sub for channel related.",pass_context=True,invoke_without_command=True)
    async def channel(self, msg):
        await self.bot.say("\n\nYou need to enter subcommand in!")

    @commands.check(is_enable)
    @commands.check(check_roles)
    @channel.command(name="create", brief="Allow to create a temp channel for relative topic.", pass_context=True, invoke_without_command=True)
    async def create_channel(self, msg, *, name:str):
        '''
        Allow User to make a channel.
        There will be time limit.
        It will then delete a channel.
        '''
        print(msg.message.server)
        server_id = msg.message.server.id
        if self.Temp_Count == int(await self.redis.hget("{}:Channel:Config".format(server_id),"limit")): #Checking Total channel that already created and compare to atually limit to see
            await self.bot.say_edit("There is already limit channel! Please wait!")
            return
        name = name.replace(" ","-").lower() #to prevert error due to space not allow in channel name
        check = discord.utils.find(lambda c:c.name == name, msg.message.server.channels) #Check if there is exist one, so that user can create one if there is none
        if check is None:
            data= await self.bot.create_channel(msg.message.server,name,(msg.message.server.default_role,self.everyone),(msg.message.server.me,self.admin)) #Create channel
            await self.bot.edit_channel(data,topic="Owner:{}".format(msg.message.author.name))
            await self.bot.say_edit("{} have now been created.".format(name.replace("-"," "))) #To info that this channel is created
            self.Temp_Chan.update({server_id:{name:{"Name":data,"Creator":msg.message.author.id}}}) #channel Name have channel ID and Creator (Creator ID)
            self.Temp_Count +=1 #add 1 to "Total atm" so we can keep maintain to limit channel
            loop = asyncio.get_event_loop()
            loop.call_later(int(await self.redis.hget("{}:Channel:Config".format(server_id),"time")), lambda: loop.create_task(self.timeout(server_id, name))) #Time for channel to be gone soon
        else:
            await self.bot.say_edit("It is already exist, try again!")

    @commands.check(is_enable)
    @channel.command(name="join", brief="Allow user to join channel", pass_context=True, invoke_without_command=True)
    async def join_channel(self, msg, *, name:str): #If user want to join the channel
        '''
        Allow user to join a channel
        '''
        name = name.replace(" ","-").lower() #In case user type channel join with space on name
        if not self.Temp_Chan.get(msg.message.server.id):
            return
        if name in self.Temp_Chan[msg.message.server.id]: #To ensure if channel still exist and in the list
            await self.bot.edit_channel_permissions(self.Temp_Chan[msg.message.server.id][name]["Name"],msg.message.author,allow=self.allow)
            await self.bot.say_edit("You can now view and chat in {}".format(name.replace("-"," ")))
        else:
            await self.bot.say_edit("I am afraid that didn't exist, please double check spelling and case")


    @commands.check(is_enable)
    @commands.check(check_roles)
    @channel.command(name="delete", brief="Allow user or mod delete channel", pass_context=True, invoke_without_command=True)
    async def delete_channel(self, msg, *, name:str): #Allow Admin/Mod or Creator of that channel delete it
        """
        Allow creator delete that certain channel that he have created.
        Mod/Higher up can also delete Channel as well.
        """
        name = name.replace(" ","-").lower()
        mod_bool= False
        Roles= self.redis.hgetall("{}:Channel:Config".format(msg.message.server.id))
        Roles= "{},{}".format(Roles["Admin_Roles"],Roles["Roles"])
        if name in self.Temp_Chan[msg.message.server.id]:
            for role in msg.message.author.roles:
                print(role)
                if role.name in Roles:
                    mod_bool = True
                    break
            if msg.message.author.id == self.Temp_Chan[msg.message.server.id][name]["Creator"] or mod_bool is True:
                await self.bot.delete_channel(self.Temp_Chan[msg.message.server.id][name]["Name"])
                await self.bot.say_edit("{} is now delete.".format(name.replace("-"," ")))
            else:
                await self.bot.say_edit("You do not have right to delete this!\nYou need to be either creator of {} or mod".format(name))
        else:
            await self.bot.say_edit("{} does not exist! Please double check spelling".format(name))

    async def timeout(self, id, name): #Timer, first it will warning user that they have X amount to talk here for while.
        if name not in self.Temp_Chan[id]:
            return
        if int(await self.redis.hget("{}:Channel:Config".format(id),"warning"))<= 60:
            unit = "second"
            time = int(await self.redis.hget("{}:Channel:Config".format(id),"warning"))
        else:
            unit= "minute"
            time = int(await self.redis.hget("{}:Channel:Config".format(id),"warning"))/60
            print (time)
        await self.bot.send_message(self.Temp_Chan[id][name]["Name"],"You have {} {} Left!".format(format(time,".2f"),unit))
        await asyncio.sleep(int(await self.redis.hget("{}:Channel:Config".format(id),"warning")))
        if name not in self.Temp_Chan[id]: #Double check in case user delete it before that time up
            return
        await self.bot.delete_channel(self.Temp_Chan[id][name]["Name"])

def setup(bot):
    bot.add_cog(Channel(bot))
