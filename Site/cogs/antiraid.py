from flask import Blueprint, request, redirect, url_for,flash
import logging
import utils

log = logging.getLogger("Nurevam.site")

blueprint = Blueprint('antiraid', __name__, template_folder='../templates/antiraid')

name = "Anti Raid (BETA)"
description = "Allow to monitor server and ensure there is no raid. Note: This is beta plugin"

db = None  #Database

default_option = {
    #Invite link and any link
    "invite_link": "0",
    "any_link":"0",
    "any_link_time":"300",

    #massive ping mention.
    "multi_ping":"0",
    "multi_ping_limit":10,

    #Joining user to server, checking their age
    "member_age": "0",
    "member_age_time": "3600",  # 1 hrs, it is min

    #if multi people join at once within x min and total of member joining at least y
    "multi_people": "0",
    "multi_people_limit": "10",  # if 10 join within x min, ban
    "multi_people_time": "300",  # 5 min, if ^x join within 5 min, do ban or any

    #if user spam message, count x msg and y min also checking ratio of similar
    "spam_msg": "0",
    "spam_msg_count": "10",  # if user spam 10 same/similar message within x, do action
    "spam_msg_percent": "90",  # how similar is message percent
    "spam_msg_time": "20",  # x sec limit
}
option_setting = [
                    {"id":'0',"name":"Nothing"},
                    #{"id":1,"name":"Warning"},
                    {"id":'2',"name":"Role Grant"},
                    {"id":'3',"name":"Kick"},
                    {"id":'4',"name":"Softban"},
                    {"id":'5',"name":"Ban"},
                  ]

#there will be 5 level
#0 is nothing
#1 is warning user
#2 is role grant
#3 is kick
#4 is softban
#5 is ban

@utils.plugin_page('antiraid')
def dashboard(server_id):
    info = db.hgetall("{}:AntiRaid:Config".format(server_id)) or default_option
    db_mute_role = db.smembers('{}:AntiRaid:mute_roles'.format(server_id)) or []
    get_role = utils.resource_get("/guilds/{}".format(server_id))
    guild_roles = get_role['roles']
    mute_role = list(filter(lambda r: r['name'] in db_mute_role or r['id'] in db_mute_role, guild_roles))

    return {"option_data":option_setting,"config":info,"mute_roles":mute_role,"guild_roles":guild_roles}

@blueprint.route('/update/<int:server_id>', methods=['POST'])
@utils.plugin_method
def update_antiraid(server_id):
    log.info(request.form)
    data = dict(request.form)
    data.pop("_csrf_token",None)
    role = data.pop("mute_roles",None)
    db.delete("{}:AntiRaid:mute_roles".format(server_id))
    if role is not None:
        db.sadd('{}:AntiRaid:mute_roles'.format(server_id),*role)
    old_data = data.copy()
    data = {key:value[0] for key,value in data.items() if value[0].isdigit()}
    if len(old_data) != len(data):
        flash("At least one of those values has to be positive INTEGER",'warning')
        return
    db.hmset("{}:AntiRaid:Config".format(server_id),data)
    db.sadd("Info:AntiRaid",server_id)
    flash('Settings updated!', 'success')
    return dashboard(server_id=server_id)
