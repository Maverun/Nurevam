from discord.ext import commands
from .utils import utils
from PIL import Image,ImageFont,ImageDraw
import io
import textwrap
import aiohttp
import discord

class Memes(commands.Cog):
    def __init__(self,bot):
        self.bot = bot
        self.redis = bot.db.redis

    def __local_check(self,ctx):
        return utils.is_enable(ctx,"memes")

    @commands.group(pass_context = True , brief = "A custom memes at your finest.",invoke_without_command=True)
    async def meme(self,ctx,name,top = "",bottom = ""):
        """
        allow to give a memes pictures
        for top,bottom, it need to be done via quotes
        for example
        <prefix>meme <name of memes> "That is so..." "cool!"
        """
        #If it not exist in database, it will return saying it is not exists.
        if not(name in await self.redis.smembers("{}:Memes:name".format(ctx.message.guild.id))):
            return await self.bot.say(ctx,content = "That meme does not exist!")
        #if it true, get link name from database and then start work on it
        link = await self.redis.hget("{}:Memes:link".format(ctx.message.guild.id),name)
        async with aiohttp.ClientSession() as session:
            async with session.get(link) as resp:
                if resp.status == 404:
                    return await self.bot.say(ctx,content = "I can't find a picture for this, It might have got delete long ago")
                print(resp.status)
                im = Image.open(io.BytesIO(await resp.read())) #read pic and save it to memory then declare new object called im (Image)
        width,height = im.size #Picture size
        font_size = int(10 + (width/len(str(width))/4)) #No idea what i am doing with math.
        print(font_size)
        font = ImageFont.truetype(font = "impact", size = font_size)

        #Start drawing picture
        draw = ImageDraw.Draw(im)
        # wrapping them up very nicely, so they don't go past pic.
        top_message = textwrap.wrap(top,20)
        bottom_message = textwrap.wrap(bottom,20)
        #getting textsize so we can calculate them for positions of text inside images
        widt,heit = draw.textsize("\n".join(top_message),font=font) #top message size
        widb,heib = draw.textsize("\n".join(bottom_message),font=font) #bottom message size
        top_width = (width-widt)/2
        top_height = (height - heit)/20
        bottom_width = (width-widb)/2
        bottom_height = (height - heib)

        #outline.... a Terrible code..
        draw.multiline_text((top_width - 1,top_height),"\n".join(top_message),font = font, fill = "black") #top text
        draw.multiline_text((top_width + 1,top_height),"\n".join(top_message),font = font, fill = "black") #top text
        draw.multiline_text((top_width,top_height - 1),"\n".join(top_message),font = font, fill = "black") #top text
        draw.multiline_text((top_width,top_height + 1),"\n".join(top_message),font = font, fill = "black") #top text

        draw.multiline_text((bottom_width - 1,bottom_height),"\n".join(bottom_message),font = font, fill = "black") #bottom text
        draw.multiline_text((bottom_width + 1,bottom_height),"\n".join(bottom_message),font = font, fill = "black") #bottom text
        draw.multiline_text((bottom_width,bottom_height - 1),"\n".join(bottom_message),font = font, fill = "black") #bottom text
        draw.multiline_text((bottom_width,bottom_height + 1),"\n".join(bottom_message),font = font, fill = "black") #bottom text

        #Start writing them (overlap black message)
        draw.multiline_text((top_width,top_height),"\n".join(top_message),font = font) #top text
        draw.multiline_text((bottom_width,bottom_height),"\n".join(bottom_message),font = font) #bottom text
        #saving pic to memory and then send to discord
        fp = io.BytesIO()
        data = im
        data.save(fp,format="PNG")
        fp.seek(0)
        await self.bot.say(ctx,file = discord.File(fp,filename="pic.png"))

    @meme.command(name =  "list")
    async def _list(self,ctx):
        name_list = await self.redis.smembers("{}:Memes:name".format(ctx.message.guild.id))
        return await self.bot.say(ctx,content = "\n".join(name_list))

def setup(bot):
    bot.add_cog(Memes(bot))
