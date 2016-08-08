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
    async def weather(self,city,*,country:str=""):
        """
        !weather city country
        country is optional.
        Name (latitude,longitude)
        Weather Conditions:
        Humidty: % Current Temperature: %
        Cloudiness: %   Wind Speed: m/s
        sunrise: 00:00:00 utc / sunset: 00:00:00 utc
        """
        with aiohttp.ClientSession() as session:
            if country:
                link = "http://api.openweathermap.org/data/2.5/weather?q={},{}&appid={}&units=metric".format(city,country,self.api)
            else:
                link = "http://api.openweathermap.org/data/2.5/weather?q={}&appid={}&units=metric".format(city,self.api)
            async with session.get(link) as resp:
                data = await resp.json()
                print(json.dumps(data,indent=2))
                weather = ""
                weather += "_**{city}-{Country}**_ -({lat},{lon})\n".format(city=data["name"],Country=data["sys"]["country"],lat=data["coord"]["lat"],lon=data["coord"]["lon"])
                weather += "**Weather Conditions**: {}\n".format(data["weather"][0]["description"])
                weather += "**Humidity**: {}% \t **Current Temperature**: {}°C/{}°F\n".format(data["main"]["humidity"],round(data["main"]["temp"]),round(data["main"]["temp"]*1.8+32))
                weather += "**Cloudiness**: {}\t **Wind Speed**: {} m/s\n".format(data["clouds"]["all"],data["wind"]["speed"])
                sunrise= datetime.datetime.fromtimestamp(data["sys"]["sunrise"]).strftime("%H:%M:%S")
                sunset= datetime.datetime.fromtimestamp(data["sys"]["sunset"]).strftime("%H:%M:%S")
                weather += "**Sunrise**: {} UTC / **Sunset**: {} UTC".format(sunrise,sunset)
                await self.bot.say_edit(weather)
def setup(bot):
    bot.add_cog(Weather(bot))