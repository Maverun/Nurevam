from discord.ext import commands
from .utils import utils
import json
import aiohttp
import asyncio
import datetime

def is_enable(msg): #Checking if cogs' config for this server is off or not
    return utils.is_enable(msg, "weather")


class Weather(): #Allow to welcome new members who join server. If it enable, will send them a message.
    def __init__(self,bot):
        self.bot = bot
        self.bot.say_edit = bot.says_edit
        self.api = utils.OS_Get("WEATHER")

    @commands.command(brief="Allow to give you a info of weather realtive on that locate.")
    @commands.check(is_enable)
    async def weather(self,*,locations:str="City,Country"):
        """
        !weather city,country
        country is optional.
        When include country, add comma after city name
        Name (latitude,longitude)
        Weather Conditions:
        Humidty: % Current Temperature: %
        Cloudiness: %   Wind Speed: m/s
        sunrise: 00:00:00 utc / sunset: 00:00:00 utc
        """
        locate = locations.replace(" ","_")
        with aiohttp.ClientSession() as session:
            link = "http://api.openweathermap.org/data/2.5/weather?q={}&appid={}&units=metric".format(locate,self.api)
            async with session.get(link) as resp:
                data = await resp.json()
                sunrise= datetime.datetime.fromtimestamp(data["sys"]["sunrise"]).strftime("%H:%M:%S")
                sunset= datetime.datetime.fromtimestamp(data["sys"]["sunset"]).strftime("%H:%M:%S")
                weather = "_**{0[name]}-{0[sys][country]}**_ -({0[coord][lat]},{0[coord][lon]})\n" \
                          "**Weather Conditions**: {0[weather][0][description]}\n" \
                          "**Humidity**: {0[main][humidity]}% \t **Current Temperature**: {1}°C/{2}°F\n" \
                          "**Cloudiness**: {0[clouds][all]}\t **Wind Speed**: {0[wind][speed]} m/s\n" \
                          "**Sunrise**: {3} UTC / **Sunset**: {4} UTC".format(data,round(data["main"]["temp"]),
                                                                              round(data["main"]["temp"]*1.8+32),
                                                                              sunrise,sunset)
                await self.bot.say_edit(weather)
def setup(bot):
    bot.add_cog(Weather(bot))
