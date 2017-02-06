from flask import Blueprint
import utils

blueprint = Blueprint('osu', __name__, template_folder='../templates/osu')

name = "osu"
description = "Allow bot to tell you about stats of your OSU profile"

db = None  #Database

@utils.plugin_page('osu')
def dashboard(server_id):
    return {}
