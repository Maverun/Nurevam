from osuapi import OsuApi, AHConnector
from discord.ext import commands
from .utils import utils
import discord

def is_enable(ctx):
    return utils.is_enable(ctx,"osu")

class Osu(commands.Cog):
    def __init__(self,bot):
        self.bot = bot
        self.redis = bot.db.redis
        self.api = OsuApi(utils.secret["osu"], connector=AHConnector())

    def __local_check(self,ctx):
        return utils.is_enable(ctx,"osu")

    async def get_account(self,ctx,author,isMention=False):
        setting = await self.redis.hget("Profile:{}".format(author.id),"osu")
        if setting is None and isMention:
            await self.bot.say(ctx,content="{} didn't register on <http://nurevam.site> yet! Tell him/her do it!".format(ctx.message.mentions[0].display_name))
        elif setting is None:
            await self.bot.say(ctx,content="You need to enter a name! Or you can enter your own name in your profile at <http://nurevam.site>")
        return setting

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
        account = None

        if name is None: #Checking if Name is none, then it either user itself
            account = await self.get_account(ctx, ctx.message.author)
        elif bool(ctx.message.mentions): #mention someone
            account = await self.get_account(ctx,ctx.message.mentions[0],True)
        if account is None and name is None: return #if get_account return which mean user didnt link their osu username or name is also none... this name is here in case someone wrote name instead of themself.

        results = await self.api.get_user(account if account else name)
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
                if account:
                    user = ctx.message.mentions[0] if bool(ctx.message.mentions) else ctx.message.author
                    embed.set_author(name=user, url="https://osu.ppy.sh/u/{}".format(results.user_id),icon_url=user.avatar_url)

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
