from discord.ext import commands
import asyncio

class Remind(): #Allow to welcome new members who join server. If it enable, will send them a message.
    def __init__(self,bot):
        self.bot = bot

    @commands.command(hidden=True)
    async def remindme(self,time,*,message=""):
        time = time.split(":")
        remind_time = 0
        msg = ""
        if len(time) == 3:
            if int(time[0]) >=5:
                msg = "It is gonna be over 5 hours, which may not work anymore."
                msg += "\nTime set {} hours {} minute {} second".format(time[0],time[1],time[2])
            remind_time += int(time[0])*3600 + int(time[1])*60+ int(time[2])
        elif len(time) == 2:
            remind_time += int(time[0])*60 + int(time[1])
            msg = "Time set {} minute {} second".format(time[0],time[1])
        else:
            msg = "Time set {} second".format(time[0])
            remind_time += int(time[0])

        await self.bot.say(msg,delete_after=30)
        await asyncio.sleep(remind_time)
        if not message:
            message = "you was remind for something."
        else:
            message = "You was remind for this ```fix\n{}\n```".format(message)
        await self.bot.reply(message,delete_after=30)
        print(message)

def setup(bot):
    bot.add_cog(Remind(bot))