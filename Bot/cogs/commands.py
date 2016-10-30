from discord.ext import commands
from .utils import utils
import json, inspect
import functools,re

class CommandEntry:
    __slot__ = ['name','content','guild_id']

    def __init__(self,**kwargs):
        #build instances of those variables
        self.name = kwargs.pop('name',None)
        self.content = kwargs.pop("content",None)
        self.guild_id = kwargs.pop("guild_id",None)

    def __repr__(self):
        return '<CustomCommandEntry name={0.name} content={0.content} guild_id={0.guild_id}>'.format(self)

async def custom_command_callback(entry, ctx, *args : str):
    print(entry)
    # in the entry content you can have ${user} and ${mention}
    author = ctx.message.author
    fixed = entry.content.replace('${user}', author.name).replace('${mention}', author.mention)
    print("okay")
    # find all ${N} and replace it with args[N]
    def getter(obj):
        try:
            return args[int(obj.group(1))]
        except:
            return ''

    fixed = re.sub(r'\${(\d+)}', getter, fixed)
    await ctx.bot.send_message(ctx.message.channel, fixed)

class CustomCommand(commands.Command):
    def __init__(self, **kwargs):
        self._entries = {}
        super().__init__(**kwargs)

    async def invoke(self, ctx):
        server = ctx.message.server
        if server is not None:
            entry = self._entries.get(server.id)
            if entry is None:
                return

            # update the callback called
            self.callback = functools.partial(custom_command_callback, entry)
            self.params = inspect.signature(self.callback).parameters

        await super().invoke(ctx)

class Commands(): #Allow to welcome new members who join server. If it enable, will send them a message.
    """
    A custom commands
    """
    def __init__(self,bot):
        self.bot = bot
        self.redis = bot.db.redis

    def create_command(self,entry):
        print("create_command")
        command = self.bot.get_command(entry)
        if command is None:
            print("creating command   " , entry)
            command = self.bot.command(name=entry.name, cls=CustomCommand,pass_context=True,)(custom_command_callback)
        if not isinstance(command, CustomCommand):
            raise RuntimeError('This is an already registered non-custom command.')
        print(command)
        if entry.guild_id in command._entries:
        # you can do some permission checking here, but this is outside the example's scope.
            raise RuntimeError('This is already registered as a custom command.')

        command._entries[entry.guild_id] = entry
        print(command._entries)

    @commands.command(pass_context=True)
    async def create(self,ctx,name,*,content):
        print(name)
        print(content)
        entry = CommandEntry(name=name.lower(),content=content,guild_id=ctx.message.server.id)
        self.create_command(entry)
        await self.bot.say("I have registered command {0.prefix}{1}".format(ctx,name))

    @commands.command(name = "listit")
    async def _list(self):
        print(CustomCommand._entries)

def setup(bot):
    bot.add_cog(Commands(bot))
