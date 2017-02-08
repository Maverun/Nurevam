from flask import Blueprint, render_template, request, redirect, url_for, flash
import logging
import utils

log = logging.getLogger("Nurevam.site")

blueprint = Blueprint('log', __name__, template_folder='../templates/log')

name = "log"
description = "Allow bot give you a log of what happen,edit,delete etc on channel"

db = None  #Database


@utils.plugin_page('log')
def dashboard(server_id):
    log.info("loading cog page")
    config = db.hgetall("{}:Log:Config".format(server_id))
    channel = utils.get_channel(server_id)
    if config.get("channel", False) is False:
        log_channel = server_id
    else:
        log_channel = config['channel']
    return {
        'guild_channel': channel,
        "log_channel": log_channel,
        'config': config
    }


@blueprint.route('/update/<int:server_id>', methods=['POST'])
@utils.plugin_method
def update_log(server_id):
    list_point = dict(request.form)
    list_point.pop('_csrf_token', None)
    path = "{}:Log:Config".format(server_id)
    log_bool = False
    db.delete(path)
    for x in list_point:
        if request.form.get(x):
            log_bool = True
        db.hset(path, x, request.form.get(x))
    if log_bool:
        db.sadd("Info:Log", server_id)
    flash('Settings updated!', 'success')
    log.info("Clear")
    return dashboard(server_id=server_id)
