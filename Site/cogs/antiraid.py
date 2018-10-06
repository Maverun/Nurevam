from flask import Blueprint, request, redirect, url_for,flash
import logging
import utils

log = logging.getLogger("Nurevam.site")

blueprint = Blueprint('antiraid', __name__, template_folder='../templates/antiraid')

name = "Anti Raid"
description = "Allow to monitor server and ensure there is no raid"

db = None  #Database

default_setting = {
    "spam_msg":0,
    "invite_link":0,
    "member_age":0,
}

#there will be 5 level
#0 is nothing
#1 is warning user
#2 is role grant
#3 is kick
#4 is softban
#5 is ban

@utils.plugin_page('antiraid')
def dashboard(server_id):
    info = db.hgetall("{}:AntiRaid:Config".format(server_id))
    if info is None:
        info = default_setting
    else:#updating any missing stuff
        info = default_setting.copy().update(info) #Wot?
    role = db.get("{}:AntiRaid:Config_role".format(server_id))
    return {"info":info,role:"role"}

@blueprint.route('/update/<int:server_id>', methods=['POST'])
@utils.plugin_method
def update_antiraid(server_id):
    return dashboard(server_id=server_id)
