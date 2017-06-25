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

def discourse(domain,api,username):
    try:
        r=requests.get(domain+"/latest.json?api_key={}&api_username={}".format(api,username))
        if r.status_code == 200:
            files = r.json()
            number =[]
            for x in files["topic_list"]["topics"]:
                number.append(x["id"])
            return max(number)
    except:
        pass

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
            db.set("{}:Discourse:ID".format(server_id), currently_topic)
            flash('Settings updated!', 'success')
    return dashboard(server_id = server_id)

@blueprint.route("/category/<int:server_id>")
@utils.plugin_method
def category(server_id):
    log.info("Category page require for discourse")
    domain =  db.hget("{}:Discourse:Config".format(server_id), "domain")
    default = db.hget("{}:Discourse:Config".format(server_id), "channel")
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

    guild_channel = utils.get_channel(server_id)
    log.info(guild_channel)
    default = [x["name"] for x in guild_channel if x["id"] == default][0]
    log.info("default show {}".format(default))
    server = {
        'id':server_id,
        'name':db.hget("Info:Server",server_id),
        'icon':db.hget("Info:Server_Icon",server_id)}

    r = requests.get("{}/categories.json".format(domain))
    raw_data = r.json()["category_list"]["categories"]
    data = []
    for x in raw_data: #checking subcategory and category
        category_id = str(x['id'])
        sub_id_list = x.get("subcategory_ids")
        if sub_id_list:
            category_id += "," + ",".join(str(x) for x in sub_id_list)
        data.append({"id":category_id,"name":x["name"]})
    return render_template("category.html",default_channel = default,category = data,guild_channel = guild_channel,cate_channel=channel,server=server)

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
