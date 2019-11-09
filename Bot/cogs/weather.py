from discord.ext import commands
from .utils import utils
import datetime
import aiohttp
import discord

class Weather(commands.Cog): #Allow to welcome new members who join guild. If it enable, will send them a message.
    def __init__(self,bot):
        self.bot = bot
        self.bot.say_edit = bot.say
        self.api = utils.secret["weather"]

    def __local_check(self,ctx):
        return utils.is_enable(ctx,"weather")

    @commands.command(brief="Allow to give you a info of weather realtive on that locate.")
    async def weather(self,ctx,*,locations:str="City,Country"):
        """
        !weather city,country
        country is optional.
        When include country, add comma after city name
        Will show:
        Name
        Coordinates
        Weather Conditions
        Humidity: %
        Current Temperature: %
        Cloudiness: %
        Wind Speed: m/s
        sunrise: 00:00:00 utc / sunset: 00:00:00 utc
        """
        if(locations == "City,Country"): return await self.bot.say(ctx,content = "You need to enter the city name")
        locate = locations.replace(" ","_")
        async with aiohttp.ClientSession() as session:
            link = "http://api.openweathermap.org/data/2.5/weather?q={}&appid={}&units=metric".format(locate,self.api)
            async with session.get(link) as resp:
                data = await resp.json()
                if data.get("cod") == '404':
                    return await self.bot.say(ctx,content = "{}, did you type command correctly? such as `city,country`, "
                                                            "note, it need comma for saying which country it is. You can just enter the city only.".format(data["message"]))
                icon = "https://openweathermap.org/img/w/{}.png".format(data["weather"][0]["icon"])
                sunrise= datetime.datetime.fromtimestamp(data["sys"]["sunrise"]).strftime("%H:%M:%S")
                sunset= datetime.datetime.fromtimestamp(data["sys"]["sunset"]).strftime("%H:%M:%S")

                if ctx.message.channel.permissions_for(ctx.message.guild.me).embed_links:

                    embed = discord.Embed()
                    embed.title = "{0[name]}-{0[sys][country]}".format(data)
                    embed.set_thumbnail(url = icon)
                    embed.add_field(name = "Coordinates",value = "({0[coord][lat]},{0[coord][lon]})".format(data))
                    embed.add_field(name = "Conditions", value = "{0[weather][0][description]}".format(data))
                    embed.add_field(name = "Humidity", value = "{0[main][humidity]}%".format(data))
                    embed.add_field(name = "Current Temperature", value = "{0}°C/{1}°F".format(round(data["main"]["temp"]),round(data["main"]["temp"]*1.8+32)))
                    embed.add_field(name = "Cloudiness", value = "{0[clouds][all]}".format(data))
                    embed.add_field(name = "Wind Speed", value = "{0[wind][speed]} m/s".format(data))
                    embed.set_footer(text = "Sunrise: {0} UTC and Sunset: {1} UTC".format(sunrise,sunset))
                    await self.bot.say(ctx,embed= embed)
                else:
                    weather = "_**{0[name]}-{0[sys][country]}**_ -({0[coord][lat]},{0[coord][lon]})\n" \
                          "**Weather Conditions**: {0[weather][0][description]}\n" \
                          "**Humidity**: {0[main][humidity]}% \t **Current Temperature**: {1}°C/{2}°F\n" \
                          "**Cloudiness**: {0[clouds][all]}\t **Wind Speed**: {0[wind][speed]} m/s\n" \
                          "**Sunrise**: {3} UTC / **Sunset**: {4} UTC".format(data,round(data["main"]["temp"]),
                                                                              round(data["main"]["temp"]*1.8+32),
                                                                              sunrise,sunset)

                    await self.bot.say(ctx,content = weather)
def setup(bot):
    bot.add_cog(Weather(bot))
