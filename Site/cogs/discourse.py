from flask import Blueprint, render_template,request, flash,redirect,url_for
import requests
import logging
import utils
import sys

log = logging.getLogger("Nurevam.site")

blueprint = Blueprint('discourse', __name__, template_folder='../templates/discourse')

name = "discourse"
description = "A Discourse forum! Allow Nurevam check if there is a new post, if there is one, it will post it out!"

db = None  #Database
def find_latest_topic(data):
    number = []
    for x in data["topic_list"]["topics"]:
        number.append(x["id"])
    return max(number)

def discourse(domain,api,username,query = "latest.json",api_key = "api_key="):
    try:
        r=requests.get(domain+"/{}?{}&api_username={}".format(query,api_key+api,username))
        if r.status_code == 200:
            return r.json()
        elif api_key == "api_key=":
            return discourse(domain,api,username,query = query,api_key = "api=") #mainly api_key work but sometime it wont and api also work...
    except Exception as e:
        print("Error under discourse: ",e)

@utils.plugin_page('discourse')
def dashboard(server_id):
    log.info("Discourse")
    config = db.hgetall("{}:Discourse:Config".format(server_id))
    channel = utils.get_channel(server_id)
    if config.get("channel", False) is False:
        discourse_channel = server_id
    else:
        discourse_channel = config['channel']

    if config.get("msg",False) is False:
        msg = "{title}\t\tAuthor: {author}\n{link}"
    else:
        msg = config["msg"]

    return {
        'guild_channel': channel,
        "discourse_channel": discourse_channel,
        "msg_template":str(msg.encode()).replace("\\\\","\\"),
        'config': config
        }

@blueprint.route('/update/<int:server_id>', methods=['POST'])
@utils.plugin_method
def update_discourse(server_id):
    log.info(request.form)
    domain = request.form.get('domain')
    api_key = request.form.get('api_key')
    username = request.form.get('username')
    channel = request.form.get('channel')
    msg_template = request.form.get("msg")

    if len(domain) == 0 or len(api_key) == 0 or len(username) == 0 or len(msg_template) == 0:
        flash("One of them need to be filled!", 'warning')
    else:
        db.hset("{}:Discourse:Config".format(server_id), "domain", domain.strip("/"))
        db.hset("{}:Discourse:Config".format(server_id), "api_key", api_key)
        db.hset("{}:Discourse:Config".format(server_id), "username", username)
        db.hset("{}:Discourse:Config".format(server_id), "channel", channel)
        db.hset("{}:Discourse:Config".format(server_id), "msg", msg_template)
        currently_topic = discourse(domain, api_key, username)
        if currently_topic is None:
            flash("There seem to be problem, please double check with domain,api key or username", 'warning')
        else:
            currently_topic = find_latest_topic(currently_topic)
            db.set("{}:Discourse:ID".format(server_id), currently_topic)
            flash('Settings updated!', 'success')
    return dashboard(server_id = server_id)

@blueprint.route("/category/<int:server_id>")
@utils.plugin_method
def category(server_id):
    log.info("Category page require for discourse")
    config = db.hgetall("{}:Discourse:Config".format(server_id))
    domain = config["domain"]
    default = config["channel"]
    api_key = config["api_key"]
    username = config["username"]

    channel = db.hgetall("{}:Discourse:Category".format(server_id))
    log.info("The channel is {}".format(channel))
    if domain is None:
        log.info("Missing domain, assume user didn't do set up")
        flash("You haven't finish config, please enter info in and click update!")
        return dashboard(server_id = server_id)
    elif channel is None:
        log.info("Channel is None")
        flash("There is something wrong with channel, please try set it again")
        return dashboard(server_id = server_id)

    #Getting guild channel list
    guild_channel = utils.get_channel(server_id)
    guild_channel = sorted(guild_channel,key = lambda k:k["name"])
    log.info(guild_channel)
    default = [x["name"] for x in guild_channel if x["id"] == default][0]
    log.info("default show {}".format(default))

    #Getting info about server, id, name and icon of it to display it.
    server = {
        'id':server_id,
        'name':db.hget("Info:Server",server_id),
        'icon':db.hget("Info:Server_Icon",server_id)}

    #making requests to discourse site within API to get category info so we can send topics to certain channel chosen by user.
    raw_data = discourse(domain,api_key,username,"site.json")
    if raw_data is None:
        flash("There is problem with accessing to site...","warning")
        return dashboard(server_id)
    raw_data = raw_data["categories"]

    data = []
    sub_temp = {}
    for x in raw_data: #checking subcategory and category
        category_id = x['id']
        have_sub = x.get("parent_category_id")
        if have_sub: #if it have sub, we should append to them
            sub = sub_temp.get(have_sub)
            if sub:
                sub.append({"id":str(category_id),"name":x["name"],"sub":"true"})
            else:
                sub_temp.update({have_sub:[{"id":str(category_id),"name":x["name"],"sub":"true"}]})
            continue
        data.append({"id":str(category_id),"name":x["name"],"sub":"false"})
    #getting proper fresh data after getting all sub categorys, it is doing in order.
    fresh_data = []
    for x in data:
        fresh_data.append(x)
        sub = sub_temp.get(int(x["id"]))
        if sub:
            for x in sub:
                fresh_data.append(x)
    log.debug(fresh_data)
    return render_template("category.html",default_channel = default,category = fresh_data,guild_channel = guild_channel,cate_channel=channel,server=server)

@blueprint.route('/category/update/<int:server_id>', methods=['POST'])
@utils.plugin_method
def update_category(server_id):
    try:
        data = dict(request.form)
        data.pop("_csrf_token")
        data = dict([[key,values[0]] for key,values in data.items()])
        db.delete("{}:Discourse:Category".format(server_id))
        db.hmset("{}:Discourse:Category".format(server_id),data)
        flash("Update!","success")
    except Exception as e:
        log.info("There is error\n{}".format(e))
    return redirect(url_for("discourse.category",server_id = server_id))

@blueprint.route("/trust_level/<int:server_id>")
@utils.plugin_method
def trust_level(server_id):
    #Getting info about server, id, name and icon of it to display it.
    server = {
        'id':server_id,
        'name':db.hget("Info:Server",server_id),
        'icon':db.hget("Info:Server_Icon",server_id)}

    def ar(i): #ar for assign_role,shortcut ik...
        db_assign_role = db.smembers("{}:Discourse:trust_role{}".format(server_id,i)) or []
        return list(filter(lambda r: r['name'] in db_assign_role or r['id'] in db_assign_role, guild_roles))

    get_role = utils.resource_get("/guilds/{}".format(server_id))
    guild_roles = get_role['roles']

    config = db.hgetall("{}:Discourse:Config".format(server_id))
    data = discourse(config["domain"],config["api_key"],config["username"],"groups/trust_level_0/members.json")

    if data is None:
        flash("Please Note, Nurevam cannot access to groups for some reason, maybe account you provide is not active or you forget to set config at dashboard?","warning")
        return dashboard(server_id = server_id)

    return render_template("trust_role.html",server=server,guild_roles=guild_roles,
                           assign_role1=ar(1),
                           assign_role2=ar(2),assign_role3=ar(3),assign_role4=ar(4))

@blueprint.route("/trust_level/update/<int:server_id>", methods = ['POST'])
@utils.plugin_method
def update_trust_level(server_id):
    def add_role(i):
        r =request.form.get("trust{}".format(i)).split(',')
        if len(r) > 0:
            db.sadd("{}:Discourse:trust_role{}".format(server_id,i),*r)
            return True
    isAssign = False
    for i in range(1,5):
        db.delete("{}:Discourse:trust_role{}".format(server_id, i)) #just in case
        gotAssign = add_role(i) #then add role. No need to make another loops
        if gotAssign:
            isAssign = True

    if isAssign:
        flash('Settings updated!', 'success')
        db.set("{}:Discourse:trust_bool".format(server_id),1)
    else:
        db.set("{}:Discourse:trust_bool".format(server_id), 0)

    return redirect(url_for("discourse.trust_level",server_id = server_id))

@blueprint.route("/user_link/<int:server_id>/")
@utils.require_auth
def discourse_link(server_id):
    server = {
        'id':server_id,
        'name':db.hget("Info:Server",server_id),
        'icon':db.hget("Info:Server_Icon",server_id)}
    discourse_id = db.hget("{}:Discourse:Trust_User".format(server_id),utils.session["user"]["id"])
    config = db.hgetall("{}:Discourse:Config".format(server_id))
    data = "" #setting default since user doing it first time maybe
    if discourse_id: #if user actually did link up by checking ID in database then we will get username
        data_get = discourse(config["domain"],config["api_key"],config["username"],"admin/users/{}.json".format(discourse_id))
        if data_get:
            data = data_get["username"]
    return render_template("user_link_account.html",server=server,user_name = data)

@blueprint.route("/user_link/update/<int:server_id>", methods = ['POST'])
@utils.plugin_method
def update_user_account_link(server_id):
    name = request.form.get("discourse_user")
    config = db.hgetall("{}:Discourse:Config".format(server_id))
    #we are checkig if it confirm.
    data = discourse(config["domain"],config["api_key"],config["username"],"users/{}/emails.json".format(name))
    is_pass = False
    discord_email = utils.session["user"]["email"]
    if data is None:
        flash("There is problem, I cannot check, there is likely a issue, please report this to your owner")
        return redirect(url_for("discourse.discourse_link", server_id=server_id,cog = "discourse"))
    elif discord_email == data["email"] or discord_email in data["secondary_emails"]:
        is_pass = True
    elif discord_email in [x["description"] for x in data["associated_accounts"]]:
        is_pass = True

    if is_pass is False:
        get_id = db.hget("{}:Discourse:Trust_User".format(server_id),utils.session["user"]["id"])
        if(get_id):
            db.hdel("{}:Discourse:Trust_User".format(server_id),utils.session["user"]["id"])
            db.hdel("{}:Discourse:Trust_User_ID".format(server_id),get_id)
        flash("Your email doesn't match up with discord email!","warning")
        return redirect(url_for("discourse.discourse_link", server_id=server_id,cog = "discourse"))

    #since we got email, we should also get their ID
    discourse_id = discourse(config["domain"], config["api_key"], config["username"], "/users/{}.json".format(name))
    discourse_id = discourse_id['user']['id']
    db.hset("{}:Discourse:Trust_User".format(server_id),utils.session["user"]["id"],discourse_id)
    db.hset("{}:Discourse:Trust_User_ID".format(server_id),discourse_id,utils.session["user"]["id"]) #reverse of Trust_user where it is discord ID: discourse_Id, this one is discourseID : Discord ID.
    flash("Update done!","success")
    return redirect(url_for("discourse.discourse_link",server_id=server_id))



#/groups/trust_level_0/members.json