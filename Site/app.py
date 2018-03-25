from flask import Flask,session,redirect,url_for,request,render_template,abort,jsonify,flash
from itsdangerous import JSONWebSignatureSerializer
from osuapi import OsuApi, ReqConnector
from flaskext.markdown import Markdown
from datetime import timedelta
import traceback
import importlib
import platform
import binascii
import logging
import redis
import utils
import json
import os


if platform.system() == "Windows": #due to different path for linux and window
    path = "secret.json"
else:
    path = "/home/mave/Nurevam/secret.json"

#read files and save it to secret
with open (path,"r") as f:
    secret = json.load(f)

#Getting database connected
Redis= secret["Redis"]
db = redis.Redis(host=Redis,decode_responses=True, db = 0)
#Getting Flask
app = Flask(__name__)
app.permanent_session_lifetime = timedelta(hours = 6)
app.db = db
utils.db = db
utils.session = session
md = Markdown(app) #for a markdown work, e.g FAQ

#Setting up log
log = logging.getLogger('Nurevam.site')
log.setLevel(logging.INFO)
format_log = logging.Formatter('%(asctime)s:\t%(levelname)s:\t%(name)s:\tFunction:%(funcName)s ||| MSG: %(message)s')
handler = logging.FileHandler(filename='Nurevam_site.log', encoding='utf-8', mode='w')
handler.setFormatter(format_log)
console = logging.StreamHandler()
console.setFormatter(format_log)
log.addHandler(handler)
log.addHandler(console)


class Data_info(): #dirty way.
    pass
data_info = Data_info()

app.config['SECRET_KEY'] = secret["SECRET_KEY"]
data_info.OAUTH2_CLIENT_ID = secret['OAUTH2_CLIENT_ID']
data_info.OAUTH2_CLIENT_SECRET = secret['OAUTH2_CLIENT_SECRET']
data_info.OAUTH2_REDIRECT_URI = secret.get('OAUTH2_REDIRECT_URI', 'http://localhost:5000/confirm_login')
data_info.API_BASE_URL = 'https://discordapp.com/api'
data_info.AUTHORIZATION_BASE_URL = data_info.API_BASE_URL + '/oauth2/authorize'
data_info.AVATAR_BASE_URL = "https://cdn.discordapp.com/avatars/"
data_info.ICON_BASE_URL = "https://cdn.discordapp.com/icons/"
data_info.DEFAULT_AVATAR = "https://discordapp.com/assets/1cbd08c76f8af6dddce02c5138971129.png"
data_info.DOMAIN = secret.get('VIRTUAL_HOST', 'localhost:5000')
data_info.TOKEN_URL = data_info.API_BASE_URL + '/oauth2/token'
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
data_info.headers = {"Authorization": "Bot " + secret["nurevam_token"]}
data_info.last_path = None  #getting last path so we can redirect it easily after login.
utils.data_info = data_info
osu_api = OsuApi(secret["osu"], connector=ReqConnector())

files_cogs = db.smembers("Website:Cogs")
blueprint_lib = {}

#loading cogs within dirty way, so I can test other files without need to edit this (when push to server)
for x in files_cogs:
    lib = importlib.import_module("cogs.{}".format(x))
    blueprint_lib[x] = lib
    app.register_blueprint(lib.blueprint, url_prefix="/"+x)
    lib.db = app.db
app.blueprint_lib = blueprint_lib
log.info("Loading done, {}".format(blueprint_lib.keys()))

lib = importlib.import_module("non-cogs.profile")
app.register_blueprint(lib.blueprint, url_prefix="/profile")
lib.db = app.db
lib.osu_api = osu_api


@app.template_filter('avatar')
def avatar(user):
    if user.get('avatar'):
        return data_info.AVATAR_BASE_URL + user['id'] + '/' + user['avatar'] + '.jpg'
    else:
        return data_info.DEFAULT_AVATAR

@app.before_request
def csrf_protect():
    if request.method == "POST":
        token = session.pop('_csrf_token', None)
        if not token or token != request.form.get('_csrf_token'):
            abort(403)

def generate_csrf_token():
    if '_csrf_token' not in session:
        session['_csrf_token'] = str(binascii.hexlify(os.urandom(15)))
    return session['_csrf_token']

app.jinja_env.globals['csrf_token'] = generate_csrf_token

@app.route('/dashboard/<int:server_id>')
@utils.require_auth
@utils.require_bot_admin
@utils.server_check
def dashboard(server_id):
    log.info("Dashboard currently")
    guilds = utils.get_user_guilds(session['api_token'])
    server = list(filter(lambda g: g['id']==str(server_id), guilds))[0]
    get_enable_list = db.hgetall("{}:Config:Cogs".format(server_id))
    info = [[key,values.name.title(),values.description] for key,values in blueprint_lib.items()]
    enable_plugin = [x for x in blueprint_lib if x in get_enable_list]
    info.sort(key=lambda x: x[1])
    return render_template("dashboard.html",server = server,info=info,enable_plugin = enable_plugin)

@app.route('/dashboard/<int:server_id>/<string:cog>')
def dashboard_cog(server_id,cog):
    log.info("running cog, {}, {}".format(server_id,cog))
    return blueprint_lib[cog].dashboard(server_id=server_id)

@app.route('/login')
def login():
    log.info("User is logging in")
    scope = ['identify', 'guilds']
    discord = utils.make_session(scope=scope)
    authorization_url, state = discord.authorization_url(
        data_info.AUTHORIZATION_BASE_URL,
        access_type="offline"
    )
    session['oauth2_state'] = state
    return redirect(authorization_url)

@app.route('/confirm_login')
def confirm_login():
    log.info("Checking login....")
    # Check for state and for 0 errors
    state = session.get('oauth2_state')
    if not state or request.values.get('error'):
        return redirect(url_for('index'))

    # Fetch token
    discord = utils.make_session(state=state)
    discord_token = discord.fetch_token(
        data_info.TOKEN_URL,
        client_secret=data_info.OAUTH2_CLIENT_SECRET,
        authorization_response=request.url)
    if not discord_token:
        log.info("Not clear, returning")
        return redirect(url_for('index'))

    # Fetch the user
    user = utils.get_user(discord_token)
    # Generate api_key from user_id
    serializer = JSONWebSignatureSerializer(app.config['SECRET_KEY'])
    api_key = str(serializer.dumps({'user_id': user['id']}))
    # Store api_key
    db.set('user:{}:api_key'.format(user['id']), api_key)
    # Store token
    db.set('user:{}:discord_token'.format(user['id']), json.dumps(discord_token))
    # Store api_token in client session
    api_token = {
        'api_key': api_key,
        'user_id': user['id']
    }
    session.permanent = True
    session['api_token'] = api_token
    log.info("Clear, redirect...")
    if data_info.last_path:
        return redirect(data_info.last_path)
    return redirect(url_for('after_login'))

@app.route('/login_confirm')
@utils.require_auth
def after_login():
    user = session['user']
    return render_template("after_login.html",user=user)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))
#Website Route
@app.route('/')
def index():
    info ={
        "Server":db.hlen("Info:Server"),
        "Member":db.get("Info:Total Member")}
    return render_template('/app/index.html',info=info)

@app.route('/about')
def about():
    core = "Allow to config unqiue setting for your own server! Want a help command in PM? Want Nurevam delete itself message after certain time? Custom prefix? No problem! Nurevam got your back!"
    profile = "A profile for you with global settings!"
    info = [[values.name.title(),values.description] for key,values in blueprint_lib.items()]
    info.append(["Core",core])
    info.append(["Profile",profile])
    print(info)
    info.sort(key=lambda x: x[0])
    return render_template('about.html',content=info, plugin_list = info)

@app.route('/faq')
def faq():
    with open('faq.md','r') as f:
        content = f.read()
    return render_template('faq.html',text=content)


@app.route('/tutorials')
def tutorials():
    with open('static/command ext tutorials.md','r') as f:
        content = f.read()
    return render_template('tutorials.html',text=content)

@app.route('/debug_token')
def debug_token():
    if not session.get('api_token'):
        return jsonify({'error': 'no api_token'})
    token = db.get('user:{}:discord_token'.format(session['api_token']['user_id']))
    return token


@app.route('/servers')
@utils.require_auth
def select_server():
    guild_id = request.args.get('guild_id')
    if guild_id:
        log.info("Got guild ID, {}".format(guild_id))
        return redirect(url_for('dashboard', server_id=int(guild_id)))

    user = utils.get_user(session['api_token'])
    guilds = utils.get_user_guilds(session['api_token'])
    user_servers = sorted(utils.get_user_managed_servers(user, guilds),key=lambda s: s['name'].lower())
    log.info("User servers: {}".format(user_servers))
    return render_template('select-server.html', user=user, user_servers=user_servers)

#Core
@app.route('/dashboard/core/<int:server_id>')
@utils.my_dash
def core(server_id): #UNQIUE SETTING FOR SERVER
    server = {
        'id':server_id,
        'name':db.hget("Info:Server",server_id),
        'icon':db.hget("Info:Server_Icon",server_id)
    }
    delete_msg = db.hgetall("{}:Config:Delete_MSG".format(server_id))
    if delete_msg.get("welcome",False):
        delete_msg.pop("welcome")
    whisper = db.get("{}:Config:Whisper".format(server_id))
    command_prefix = db.get("{}:Config:CMD_Prefix".format(server_id))
    if command_prefix is None:
        command_prefix = "!"
    return render_template('core.html',server=server,config_delete=delete_msg,whisper=whisper,command_prefix=command_prefix)

@app.route('/dashboard/core/<int:server_id>/update', methods=['POST'])
@utils.plugin_method
def update_core(server_id):
    config_delete = db.hgetall("{}:Config:Delete_MSG".format(server_id))
    print(config_delete)
    for x in config_delete:
        print(request.form.get(x))
        db.hset("{}:Config:Delete_MSG".format(server_id),x,request.form.get(x))
    db.set("{}:Config:Whisper".format(server_id),request.form.get("whisper"))
    db.set("{}:Config:CMD_Prefix".format(server_id),request.form.get("command_prefix"))
    flash('Settings updated!', 'success')
    return redirect(url_for('core', server_id=server_id))

@app.before_first_request
def setup_logging():
    try:
        log.info("\033[92mName: {}|||ID: {}\033[00m".format(session["user"]["username"],session["user"]["id"]))
    except:
        pass

@app.errorhandler(401)
def code_401(e):
    #if there is error with 401, it would redirect you to login pages
    #It happen when you login in other area other than your site.
    return redirect("/login")

@app.errorhandler(404)
def code_404(e):
    #If page is not found, it will info you that page is not found.
    return render_template("error/code_404_not_found.html")

@app.errorhandler(500)
def code_500(e):
    return render_template("error/code_500_internal_error.html")

if __name__ == '__main__':
    app.debug = True
    app.run()
