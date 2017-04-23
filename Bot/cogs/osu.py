from osuapi import OsuApi, AHConnector
from discord.ext import commands
from .utils import utils
import discord

def is_enable(ctx):
    return utils.is_enable(ctx,"osu")

class Osu:
    def __init__(self,bot):
        self.bot = bot
        self.redis = bot.db.redis
        self.api = OsuApi(utils.secret["osu"], connector=AHConnector())

    def __local_check(self,ctx):
        return utils.is_enable(ctx,"osu")

    @commands.command(pass_context=True,brief="Prints a stats of player's")
    async def osu(self,ctx,name=None):
        """
        Links an osu! profile with additional info.
        Name: #rank
        Level:  , PP:
        Country: #rank
        Total Play:
        Rank Score:
        Total Score:
        You can enter your username on the Nurevam site, so that Nurevam cant automatically link your profile.
        """

        boolean = False
        mention = False
        user = ctx.message.author
        if ctx.message.mentions: #If mention is true, it will get from mention ID instead.
            user = ctx.message.mentions[0]
            user = user
            mention = True
        setting = await self.redis.hget("Profile:{}".format(user.id),"osu")
        if name is None: #if name is None then meaning it is in profile.
            if setting is None: #If it not found in profile, meaning it wasn't enter in
                await self.bot.say(ctx, content = "You need to enter a name! Or you can enter your own name in your profile at <http://nurevam.site>")
            else: # If it in setting, it is true.
                boolean = True
                name = setting
        else: #other wise, name have called, check if it mention or not
            if mention: # if name was a mention, (boolean check)
                if setting is None: #if setting is not found, not in data
                    await self.bot.say(ctx,content = "{} didn't register on <http://nurevam.site> yet! Tell him/her do it!".format(ctx.message.mentions[0].display_name))
                else: #if it true, it is in data
                    name = setting
                    boolean = True
            else:
                   boolean = True
        if boolean:
            results =(await self.api.get_user(name))
            if results:
                results = results[0]
                description = "**Level**: {0.level}, **PP**: {0.pp_raw}\n" \
                          "**Country**: {0.country} #{0.pp_country_rank}\n" \
                          "**Total Play**: {0.playcount}\n"\
                          "**Rank Score**: {0.ranked_score}\n" \
                          "**Total Score**: {0.total_score}\n".format(results)
                if ctx.message.channel.permissions_for(ctx.message.guild.me).embed_links:
                    embed = discord.Embed()
                    embed.colour = 0xFF66AA
                    # if user.color:
                    #     embed.colour = user.color.value
                    if setting:
                        embed.set_author(name = user,url="https://osu.ppy.sh/u/{}".format(results.user_id),icon_url=user.avatar_url)

                    embed.set_thumbnail(url = "https://a.ppy.sh/{}".format(results.user_id))
                    embed.title = "**{0.username}: #{0.pp_rank}**".format(results)
                    embed.url ="https://osu.ppy.sh/u/{}".format(results.user_id)
                    embed.description = description
                    await self.bot.say(ctx,embed = embed)
                else:
                    msg = "{0.username}: #{0.pp_rank}\n".format(results)+description
                    link = "<https://osu.ppy.sh/u/{0}>\nhttps://a.ppy.sh/{0}".format(results.user_id)
                    await self.bot.say(ctx, content = "```xl\n{}\n```{}".format(msg,link))
            else:
                await self.bot.say(ctx,content = "I am sorry, but that name does not exist.")
def setup(bot):
    bot.add_cog(Osu(bot))
