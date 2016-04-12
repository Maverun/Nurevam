from .Utils import Read

def Setup(): #Rerun those for refresh variables when reload
    global Main_Config
    global Config
    global Bot_Config
    Main_Config= Read.config
    Config= Read.Bot_Config["Config"]
    Bot_Config=Read.Bot_Config

class Greet():
    def __init__(self,bot):
        self.bot = bot
        if Bot_Config["Config"]["Greet"]["Enable"] == "on":
            self.bot.add_listener(self.Greet_Message,"on_member_join")
    Setup()

    async def Greet_Message(self,member):
        print(member)
        if Bot_Config["Config"]["Greet"]["Whisper"] == "on":
            await self.bot.send_message(member,Bot_Config["Config"]["Greet"]["Message"].format(member,member.mention))
        else:
            await self.bot.send_message(self.bot.get_channel(member.server.id),Bot_Config["Config"]["Greet"]["Message"].format(member,member.mention))

def setup(bot):
    bot.add_cog(Greet(bot))