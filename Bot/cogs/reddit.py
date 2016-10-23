from discord.ext import commands
import praw
import json
import asyncio

class Reddit(): #Allow to welcome new members who join server. If it enable, will send them a message.
    def __init__(self,bot):
        self.bot = bot
        self.praw = praw.Reddit(user_agent='Nurevam')
        # self.praw.login(disable_warning=True)
        self.bot.say_edit = bot.says_edit

    @commands.command()
    async def username(self,name):
        user = self.praw.get_redditor(name)
        await self.bot.says_edit("```xl\n{}: Link Karma: {} Comment Karma:{}\n```\n<https://www.reddit.com/user/{}>".format(name,user.link_karma,user.comment_karma,name))

    @commands.command()
    async def sub(self):
        subreddit = self.praw.get_redditor("learnpython")
        print(subreddit.get_hot(limit=5))
def setup(bot):
    bot.add_cog(Reddit(bot))






