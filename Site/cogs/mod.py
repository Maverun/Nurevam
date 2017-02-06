from flask import Blueprint, render_template,request, redirect,url_for
import logging
import utils

log = logging.getLogger("Nurevam.site")

blueprint = Blueprint('mod', __name__, template_folder='../templates/mod')

name = "mod"
description = "A simple mod command, allow to clean message! Be itself,role,person or all!"

db = None  #Database

@utils.plugin_page('mod')
def dashboard(server_id):
    log.info("Load cogs pages")
    db_admin_role = db.smembers('{}:Mod:admin_roles'.format(server_id)) or []
    get_role = utils.resource_get("/guilds/{}".format(server_id))
    guild_roles = get_role['roles']
    admin_role = list(filter(lambda r: r['name'] in db_admin_role or r['id'] in db_admin_role, guild_roles))
    return {"admin_roles": admin_role, "guild_roles": guild_roles}

@blueprint.route('/update/<int:server_id>', methods=['POST'])
@utils.plugin_method
def update_mod(server_id):
    admin_roles = request.form.get('admin_roles').split(',')
    db.delete("{}:Mod:admin_roles".format(server_id))
    if len(admin_roles) > 0:
        db.sadd("{}:Mod:admin_roles".format(server_id), *admin_roles)
    return redirect(url_for('plugin_mod', server_id=server_id))
