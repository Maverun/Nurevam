from flask import Blueprint
import random
import utils

anime_picture=[["http://31.media.tumblr.com/tumblr_m3z4xrHVZi1rw2jaio1_500.gif","I will wait for your commands! <3"],
["http://media3.giphy.com/media/ErZ8hv5eO92JW/giphy.gif","NICE JAB! USE IT AS YOU WANT!"]]


blueprint = Blueprint('myanimelist',__name__,template_folder='../templates/myanimelist')

name = "Anime and Manga"
description = "Search the web for your favorite anime and manga."

db = None #Database

#Anime
@utils.plugin_page("myanimelist")
def dashboard(server_id):
    number =random.randint(0,len(anime_picture)-1)
    get_role = utils.resource_get("/guilds/{}".format(server_id))
    guild_roles = get_role['roles']
    role = db.smembers('{}:Memes:editor_role'.format(server_id)) or []
    channel = utils.get_channel(server_id)
    admin_role = list(filter(lambda r: r['name'] in role or r['id'] in role, guild_roles))
    return {"Info":anime_picture[number],"guild_roles":guild_roles,"admin_roles":admin_role,"channel":channel}
