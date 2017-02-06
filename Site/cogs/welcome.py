from flask import Blueprint, request, redirect, url_for,flash
import logging
import utils

log = logging.getLogger("Nurevam.site")

blueprint = Blueprint('welcome', __name__, template_folder='../templates/welcome')

name = "welcome"
description = "Send a welcome/greet message to newcomer who just join your server!"

db = None  #Database

@utils.plugin_page('welcome')
def dashboard(server_id):
    log.info("loading cogs page")
    default_message = "{user}, welcome to **{server}**!"
    get_message = db.hget("{}:Welcome:Message".format(server_id), "message")
    if get_message is None:
        db.hset("{}:Welcome:Message".format(server_id), "message", default_message)
        get_message = default_message
    config = db.hgetall("{}:Welcome:Message".format(server_id))
    channel = utils.get_channel(server_id)
    delete_msg = db.hget("{}:Welcome:Message".format(server_id), "delete_msg") or 0
    if config.get("channel", False) is False:
        welcome_channel = server_id
    else:
        welcome_channel = config['channel']

    db_assign_role = db.smembers('{}:Welcome:Assign_Roles'.format(server_id)) or []
    get_role = utils.resource_get("/guilds/{}".format(server_id))
    guild_roles = get_role['roles']
    assign_role = list(filter(lambda r: r['name'] in db_assign_role or r['id'] in db_assign_role, guild_roles))
    return {
        'guild_channel': channel,
        "welcome_channel": welcome_channel,
        'assign_role': assign_role,
        'guild_roles': guild_roles,
        'message': get_message,
        'config': config,
        'delete_msg': delete_msg}


@blueprint.route('/update', methods=['POST'])
@utils.plugin_method
def update_welcome(server_id):
    welcome_message = request.form.get('message')
    channel = request.form.get('channel')
    whisper_options = request.form.get('whisper')
    role_options = request.form.get("role")
    role_id = request.form.get("assign_role").split(',')
    delete_msg = request.form.get('delete_msg')
    delete_options = request.form.get("enable_delete")
    enable_msg = request.form.get("enable_message")
    if len(welcome_message) >= 2000 or welcome_message == "":
        flash("The welcome message need to be between 1-2000!", 'warning')
    else:
        try:
            delete_msg = int(delete_msg)
        except ValueError:
            flash('The delete message that you provided isn\'t an integer!', 'warning')
            return redirect(url_for('plugin_welcome', server_id=server_id))
        db.hset('{}:Welcome:Message'.format(server_id), 'message', welcome_message)
        db.hset('{}:Welcome:Message'.format(server_id), 'channel', channel)
        db.hset('{}:Welcome:Message'.format(server_id), 'whisper', whisper_options)
        db.hset('{}:Welcome:Message'.format(server_id), 'delete_msg', delete_msg)
        db.hset('{}:Welcome:Message'.format(server_id), 'enable_delete', delete_options)
        db.hset('{}:Welcome:Message'.format(server_id), 'enable_message', enable_msg)
        flash('Settings updated!', 'success')
    db.hset('{}:Welcome:Message'.format(server_id), 'role', role_options)
    db.delete("{}:Welcome:Assign_role".format(server_id))
    if len(role_id) > 0:
        db.sadd("{}:Welcome:Assign_Roles".format(server_id), *role_id)
    return redirect(url_for('plugin_welcome', server_id=server_id))
