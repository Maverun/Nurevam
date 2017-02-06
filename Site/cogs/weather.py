from flask import Blueprint
import utils

blueprint = Blueprint('weather', __name__, template_folder='../templates/weather')

name = "weather"
description = "Allow bot to tell you stats in city you ask for"

db = None  #Database


@utils.plugin_page('weather')
def dashboard(server_id):
    return {}
