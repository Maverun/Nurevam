from flask import Blueprint, render_template, request, redirect, url_for, flash
import requests
import logging
import utils

log = logging.getLogger("Nurevam.site")


blueprint = Blueprint('memes', __name__, template_folder='../templates/memes')

name = "memes"
description = "Allow to post a custom memes you like!"

db = None  #Database


@utils.plugin_page('memes')
def dashboard(server_id):
    log.info("loading cog pages")
    db_role = db.smembers('{}:Memes:editor_role'.format(server_id)) or []
    get_role = utils.resource_get("/guilds/{}".format(server_id))
    guild_roles = get_role['roles']
    role = list(filter(lambda r: r['name'] in db_role or r['id'] in db_role, guild_roles))
    return {"roles": role, "guild_roles": guild_roles}


@blueprint.route('/update/<int:server_id>', methods=['POST'])
@utils.plugin_method
def update_memes(server_id):
    roles = request.form.get('roles').split(',')
    db.delete("{}:Memes:editor_role".format(server_id))
    if len(roles) > 0:
        db.sadd("{}:Memes:editor_role".format(server_id), *roles)
    return redirect(url_for('plugin_memes', server_id=server_id))


def check_memes_link(link):
    try:
        r = requests.get(link)
    except:
        flash("There is somthing wrong with a link...", "warning")
        return 2
    if r.status_code == 200:
        if r.headers['content-type'] in ['image/png', 'image/jpeg']:
            return 0  # to say it is True
        elif r.headers == 'image/gif':
            flash("Gif memes are not support!", "warning")
            return 1  # to say it is not support yet for gif... some day?
    flash("This type of files does not support!", "warning")
    return 2  # return False


@blueprint.route("/<string:cog>/<int:server_id>/")
@utils.require_role
def memes(cog, server_id):
    meme_link = db.hgetall("{}:Memes:link".format(server_id))
    return render_template("memes.html", data_memes=meme_link, server_id=server_id)


@blueprint.route('/add/<string:cog>/<int:server_id>/', methods=['POST'])
@utils.require_role
def add_memes(cog, server_id):
    name = request.form.get("meme_name")
    link = request.form.get("meme_link")
    status = check_memes_link(link)
    if status == 0:  # if is true
        if name in db.smembers("{}:Memes:name".format(server_id)):
            flash("This name already exists!", "warning")
        else:
            db.hset("{}:Memes:link".format(server_id), name, link)
            db.sadd("{}:Memes:name".format(server_id), name)
            flash("You have add a new memes!", "success")
    return redirect(url_for("memes", server_id=server_id, cog="memes"))


@blueprint.route('/update/<int:server_id>/<string:name>', methods=['POST'])
@utils.plugin_method
def edit_memes(server_id, name):
    new_name = request.form.get("meme_name")
    link = request.form.get("meme_link")
    status = check_memes_link(link)
    if status == 0:
        # delete old database
        db.hdel("{}:Memes:link".format(server_id), name)
        db.srem("{}:Memes:name".format(server_id), name)
        # adding, if there is a way to rename them in hash, that would be great...
        db.hset("{}:Memes:link".format(server_id), new_name, link)
        db.sadd("{}:Memes:name".format(server_id), new_name)
        flash("Update data!", "success")
    return redirect(url_for("memes", server_id=server_id, cog="memes"))


@blueprint.route('/delete/<int:server_id>/<string:name>/', methods=['GET'])
@utils.plugin_method
def delete_memes(server_id, name):
    # Deleting data
    db.hdel("{}:Memes:link".format(server_id), name)
    db.srem("{}:Memes:name".format(server_id), name)
    return redirect(url_for("memes", server_id=server_id, cog="Memes"))

