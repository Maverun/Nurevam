from flask import Blueprint, render_template, request, redirect, url_for, flash
import logging
import utils

log = logging.getLogger("Nurevam.site")

limit = 25 #original was 10.


blueprint = Blueprint('customcmd', __name__, template_folder='../templates/custom commands')

name = "custom commands"
description = "Allow to use custom command, create command as you like!"

db = None  #Database


@utils.plugin_page('custom commands')
def dashboard(server_id):
    log.info("loading cog pages")
    db_role = db.smembers('{}:Customcmd:editor_role'.format(server_id)) or []
    get_role = utils.resource_get("/guilds/{}".format(server_id))
    guild_roles = get_role['roles']
    role = list(filter(lambda r: r['name'] in db_role or r['id'] in db_role, guild_roles))

    role_max = db.hgetall("{}:Customcmd:role".format(server_id)) or {}
    temp = [
        {"name":x['name'],
         "id":x['id'],
          "color":hex(x["color"]).split("0x")[1],
         "max":role_max.get(x["id"],0)} for x in guild_roles]
    temp.sort(key=lambda x: x['name'])
    role_max_use = [temp[:int(len(temp)/2)],temp[int(len(temp)/2):]] #Spliting them into half
    return {"roles": role, "guild_roles": guild_roles,"role_max":role_max_use,"limit":limit}


@blueprint.route('/update/<int:server_id>', methods=['POST'])
@utils.plugin_method
def update_customcmd(server_id):
    log.info("updating")
    data = dict(request.form)
    data.pop("_csrf_token") #so we can focus on role easier
    able_role = []
    all_role = {}
    for key,values in data.items():
        if "req_role_" in key:
            key = key.strip("req_role_")
            if values[0].isdigit():
                all_role[key] = values[0]
                if int(values[0]) > 0 and int(values[0]) <= limit: #for now, limit is max for each role
                    able_role.append(key)
                else:
                    if int(values[0]) > limit:
                        flash("You cannot have more than {} uses!".format(limit))
                        return dashboard(server_id=server_id)
                    elif int(values[0]) < 0:
                        flash("uhh number cannot be negative!","warning")
                        return dashboard(server_id=server_id)
            else:
                flash("Role must have integer number!","warning")

    db.delete("{}:Customcmd:editor_role".format(server_id))
    if able_role:
        log.info("Able role are {}".format(able_role))
        db.sadd("{}:Customcmd:editor_role".format(server_id),*able_role)
    db.hmset("{}:Customcmd:role".format(server_id),all_role)
    flash("Settings updated!","success")
    log.info("returning")
    return dashboard(server_id=server_id)

def max_use(server_id):
    user = utils.session.get('user')
    role_data = db.hgetall("{}:Customcmd:role".format(server_id))
    get_user_role = utils.resource_get("/guilds/{}/members/{}".format(server_id,user['id']))["roles"]
    use = []
    for role,num in role_data.items():
        if role in get_user_role:
            use.append(num)
    if use:
        max_cmd = max([int(x) for x in use])
    else:
        max_cmd = 0
    return max_cmd


@blueprint.route("/<string:cog>/<int:server_id>/")
@utils.require_role
def customcmd(cog, server_id):
    is_admin = utils.is_admin(server_id)
    owner = utils.session["user"]["id"]
    customcmd_content = db.hgetall("{}:Customcmd:content".format(server_id))
    customcmd_brief = db.hgetall("{}:Customcmd:brief".format(server_id))
    customcmd_owner = db.hgetall("{}:Customcmd:owner".format(server_id))
    current_use = db.hget("{}:Customcmd:owner_use".format(server_id),owner) or 0
    use = max_use(server_id)
    content = {}
    brief = {}

    if customcmd_content:
        customcmd_content = dict([x,str(y.encode()).replace("\\\\","\\")] for x,y in customcmd_content.items()) #a way to fix escape term. terrible yeh

    if is_admin: #if someone is admin, they can view all
        log.info("It is admin person")
        member = db.hgetall("Info:Name")
        content = customcmd_content
        brief = customcmd_brief
        owner = {}
        for name,_id in customcmd_owner.items():
            owner[name] = member.get(_id,"UNKNOWN") #getting member name WHILE checking left member
    else:
        log.info("Not admin person")
        for cmd in customcmd_content:#running check each commands to filter out to owner only
            if customcmd_owner[cmd] == owner:
                content[cmd] = customcmd_content[cmd]
                brief[cmd] = customcmd_brief[cmd]
        owner = "none"
    return render_template("customcmd.html", data_customcmd=content,data_brief = brief,
                           server_id=server_id,max_use = use,current =  current_use,cmd_owner = owner, cog = "customcmd")


@blueprint.route('/add/<string:cog>/<int:server_id>/', methods=['POST'])
@utils.require_role
def add_customcmd(cog, server_id):
    log.info("Making comment")
    name = request.form.get("cmd_name")
    content = request.form.get("cmd_content")
    brief = request.form.get("cmd_brief")

    current_use = db.hget("{}:Customcmd:owner_use".format(server_id),utils.session["user"]["id"]) or 0
    use = max_use(server_id)

    if int(current_use) >= use:
        flash("You have created enough commands!","warning")
        return redirect(url_for("customcmd.customcmd",server_id = server_id, cog = "customcmd"))

    if name == "":
        flash("Name cannot be blank!","warning")
    elif name in db.smembers("{}:Customcmd:name".format(server_id)):
        flash("This name already exists!", "warning")
    else: #if No problem, will make commands, update of content, brief, owner and list of commands
        db.hset("{}:Customcmd:content".format(server_id), name, content)
        db.hset("{}:Customcmd:brief".format(server_id), name, brief)
        db.hset("{}:Customcmd:owner".format(server_id), name, utils.session["user"]["id"])
        db.sadd("{}:Customcmd:name".format(server_id), name)
        db.set("{}:Customcmd:update".format(server_id), "yes")
        db.hincrby("{}:Customcmd:owner_use".format(server_id),utils.session["user"]["id"])
        flash("You have add a new command!", "success")

    return redirect(url_for("customcmd.customcmd", server_id=server_id, cog="customcmd"))


@blueprint.route('/update/<string:cog>/<int:server_id>/<string:name>', methods=['POST'])
@utils.require_role
def edit_customcmd(cog,server_id, name):
    print("Debuging, edit custom commands.")
    new_name = request.form.get("cmd_name")
    content = request.form.get("cmd_content")
    brief = request.form.get("cmd_brief")
    if new_name == "":
        flash("Name cannot be blank!","warning")
    else:
        # delete old database
        db.hdel("{}:Customcmd:content".format(server_id), name)
        db.hdel("{}:Customcmd:brief".format(server_id), name)
        db.hdel("{}:Customcmd:owner".format(server_id), name)
        db.srem("{}:Customcmd:name".format(server_id), name)
        # adding, if there is a way to rename them in hash, that would be great...
        db.hset("{}:Customcmd:content".format(server_id), new_name, content)
        db.hset("{}:Customcmd:brief".format(server_id), new_name, brief)
        db.hset("{}:Customcmd:owner".format(server_id), new_name, utils.session["user"]["id"])
        db.sadd("{}:Customcmd:name".format(server_id), new_name)
        db.sadd("{}:Customcmd:update_delete".format(server_id), new_name)
        flash("Update from {} to {}!".format(name,new_name), "success")
    return redirect(url_for("customcmd.customcmd", server_id=server_id, cog="customcmd"))


@blueprint.route('/delete/<string:cog>/<int:server_id>/<string:name>/', methods=['GET'])
@utils.require_role
def delete_customcmd(cog,server_id, name):
    # Deleting data
    db.hdel("{}:Customcmd:content".format(server_id), name)
    db.hdel("{}:Customcmd:brief".format(server_id), name)
    db.hdel("{}:Customcmd:owner".format(server_id), name)
    db.hincrby("{}:Customcmd:owner_use".format(server_id), utils.session["user"]["id"],amount = -1)
    db.srem("{}:Customcmd:name".format(server_id), name)
    db.sadd("{}:Customcmd:update_delete".format(server_id), name)

    flash("{} is deleted now".format(name),"success")
    return redirect(url_for("customcmd.customcmd", server_id=server_id, cog="customcmd"))

