from flask import Flask, session, request, url_for, render_template, redirect, \
jsonify, make_response, flash, abort, Response
from flaskext.markdown import Markdown
from itsdangerous import JSONWebSignatureSerializer
from requests_oauthlib import OAuth2Session
from functools import wraps
import logging
import random
import redis
import os
import json
import binascii
import requests
import math

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY")
md = Markdown(app) #for a markdown work, e.g FAQ

Redis= os.environ.get('Redis')
OAUTH2_CLIENT_ID = os.environ.get('OAUTH2_CLIENT_ID')
OAUTH2_CLIENT_SECRET = os.environ.get('OAUTH2_CLIENT_SECRET')
OAUTH2_REDIRECT_URI = os.environ.get('OAUTH2_REDIRECT_URI', 'http://localhost:5000/confirm_login')
API_BASE_URL = os.environ.get('API_BASE_URL', 'https://discordapp.com/api')
AUTHORIZATION_BASE_URL = API_BASE_URL + '/oauth2/authorize'
AVATAR_BASE_URL = "https://cdn.discordapp.com/avatars/"
ICON_BASE_URL = "https://cdn.discordapp.com/icons/"
DEFAULT_AVATAR = "https://discordapp.com/assets/1cbd08c76f8af6dddce02c5138971129.png"
DOMAIN = os.environ.get('VIRTUAL_HOST', 'localhost:5000')
TOKEN_URL = API_BASE_URL + '/oauth2/token'
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
headers = {"Authorization": os.environ.get("NUREVAM_TOKEN")}

db = redis.Redis(host=Redis,decode_responses=True)

#ANIME PICTURE
anime_picture=[["http://31.media.tumblr.com/tumblr_m3z4xrHVZi1rw2jaio1_500.gif","I will wait for your commands! <3"],
               ["http://media3.giphy.com/media/ErZ8hv5eO92JW/giphy.gif","NICE JAB! USE IT AS YOU WANT!"]]



def resource_get(end):#Getting a resournces from API
    r = requests.get(API_BASE_URL+end,headers=headers)
    return r.json()
"""
    JINJA2 Filters
"""

@app.template_filter('avatar')
def avatar(user):
    if user.get('avatar'):
        return AVATAR_BASE_URL + user['id'] + '/' + user['avatar'] + '.jpg'
    else:
        return DEFAULT_AVATAR

"""
    Discord DATA logic
"""

def get_user(token):
    # If it's an api_token, go fetch the discord_token
    if token.get('api_key'):
        discord_token_str = db.get('user:{}:discord_token'.format(token['user_id']))
        token = json.loads(discord_token_str)

    discord = make_session(token=token)

    req = discord.get(API_BASE_URL + '/users/@me')
    if req.status_code != 200:
        abort(req.status_code)

    user = req.json()
    # Saving that to the session for easy template access
    session['user'] = user

    # Saving that to the db
    db.sadd('users', user['id'])
    db.set('user:{}'.format(user['id']), json.dumps(user))
    return user

def get_user_guilds(token):
    # If it's an api_token, go fetch the discord_token
    if token.get('api_key'):
        user_id = token['user_id']
        discord_token_str = db.get('user:{}:discord_token'.format(token['user_id']))
        token = json.loads(discord_token_str)
    else:
        user_id = get_user(token)['id']

    discord = make_session(token=token)

    req = discord.get(API_BASE_URL + '/users/@me/guilds')
    if req.status_code != 200:
        abort(req.status_code)

    guilds = req.json()
    # Saving that to the db
    db.set('user:{}:guilds'.format(user_id), json.dumps(guilds))
    return guilds

def get_user_managed_servers(user, guilds):
    return list(filter(lambda g: (g['owner'] is True) or bool(( int(g['permissions'])>> 5) & 1), guilds))

"""
    CRSF Security
"""

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

"""
    AUTH logic
"""

def token_updater(discord_token):
    user = get_user(discord_token)
    # Save the new discord_token
    db.set('user:{}:discord_token'.format(user['id']), json.dumps(discord_token))

def make_session(token=None, state=None, scope=None):
    return OAuth2Session(
        client_id=OAUTH2_CLIENT_ID,
        token=token,
        state=state,
        scope=scope,
        redirect_uri=OAUTH2_REDIRECT_URI,
        auto_refresh_kwargs={
            'client_id': OAUTH2_CLIENT_ID,
            'client_secret': OAUTH2_CLIENT_SECRET,
        },
        auto_refresh_url=TOKEN_URL,
        token_updater=token_updater
    )

@app.route('/login')
def login():
    scope = ['identify', 'guilds']
    discord = make_session(scope=scope)
    authorization_url, state = discord.authorization_url(
        AUTHORIZATION_BASE_URL,
        access_type="offline"
    )
    session['oauth2_state'] = state
    print(state)
    return redirect(authorization_url)

@app.route('/confirm_login')
def confirm_login():
    # Check for state and for 0 errors
    state = session.get('oauth2_state')
    if not state or request.values.get('error'):
        return redirect(url_for('index'))

    # Fetch token
    discord = make_session(state=state)
    discord_token = discord.fetch_token(
        TOKEN_URL,
        client_secret=OAUTH2_CLIENT_SECRET,
        authorization_response=request.url)
    if not discord_token:
        return redirect(url_for('index'))

    # Fetch the user
    user = get_user(discord_token)
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
    return redirect(url_for('after_login'))

def require_auth(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        # Does the user have an api_token?
        api_token = session.get('api_token')
        if api_token is None:
            return redirect(url_for('login'))

        # Does his api_key is in the db?
        user_api_key = db.get('user:{}:api_key'.format(api_token['user_id']))
        if user_api_key != api_token['api_key']:
            return redirect(url_for('login'))

        return f(*args, **kwargs)
    return wrapper

@app.route('/login_confirm')
@require_auth
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
        "Server":db.get("Info:Total Server"),
        "Member":db.get("Info:Total Member")}
    return render_template('index.html',info=info)
@app.route('/about')
def about():
    content = []
    with open("static/about.txt",'r') as f:
        for line in f.readlines():
            print(line)
            if line.startswith("#"):
                print("ignore")
                continue
            elif len(line.split(",")) == 2:
                content.append(line.split(","))
    return render_template('about.html',content=content)

@app.route('/faq')
def faq():
    with open('faq.md','r') as f:
        content = f.read()
    return render_template('faq.html',text=content)

@app.route('/debug_token')
def debug_token():
    if not session.get('api_token'):
        return jsonify({'error': 'no api_token'})
    token = db.get('user:{}:discord_token'.format(session['api_token']['user_id']))
    return token

@app.route('/profile')
@require_auth
def profile():
    """
    A user profile.
    It's purpose is for globals setting across server.
    """
    user = session['user']
    setting = db.hgetall("Profile:{}".format(user["id"]))
    return render_template('profile.html',user=user,setting=setting)

@app.route('/profile/update', methods=['POST'])
@require_auth
def update_profile(): #Update a setting.
    list_point = dict(request.form)
    list_point.pop('_csrf_token',None)
    path = "Profile:{}".format(session['user']['id'])
    for  x in list_point:
        if request.form.get(x) == "":
            db.hdel(path,x)
            continue
        if x == "myanimelist":
            status = status_site("http://myanimelist.net/profile/{}".format(request.form.get(x)))
            if status is False:
                continue
        db.hset(path,x,request.form.get(x))
    flash('Settings updated!', 'success')
    return redirect(url_for('profile'))

def status_site(site):
    r = requests.get(site)
    if r.status_code == 200:
        return True
    else:
        return False

@app.route('/servers')
@require_auth
def select_server():
    guild_id = request.args.get('guild_id')
    if guild_id:
        return redirect(url_for('dashboard', server_id=int(guild_id)))

    user = get_user(session['api_token'])
    guilds = get_user_guilds(session['api_token'])
    user_servers = sorted(
        get_user_managed_servers(user, guilds),
        key=lambda s: s['name'].lower()
    )
    return render_template('select-server.html', user=user, user_servers=user_servers)

def server_check(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        server_id = kwargs.get('server_id')
        server_ids = db.hget("Info:Server",server_id)

        if server_ids is None:
            url =   "https://discordapp.com/oauth2/authorize?&client_id={}"\
                    "&scope=bot&permissions={}&guild_id={}&response_type=code"\
                    "&redirect_uri=http://{}/servers".format(
                        OAUTH2_CLIENT_ID,
                        '66321471',
                        server_id,
                        DOMAIN
                    )
            return redirect(url)

        return f(*args, **kwargs)
    return wrapper

def require_bot_admin(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        server_id = kwargs.get('server_id')
        user = get_user(session['api_token'])
        guilds = get_user_guilds(session['api_token'])
        user_servers = get_user_managed_servers(user, guilds)
        if str(server_id) not in map(lambda g: g['id'], user_servers):
            return redirect(url_for('select_server'))

        return f(*args, **kwargs)
    return wrapper


#####################################################
#    _____    _                   _                 #
#   |  __ \  | |                 (_)                #
#   | |__) | | |  _   _    __ _   _   _ __    ___   #
#   |  ___/  | | | | | |  / _` | | | | '_ \  / __|  #
#   | |      | | | |_| | | (_| | | | | | | | \__ \  #
#   |_|      |_|  \__,_|  \__, | |_| |_| |_| |___/  #
#                          __/ |                    #
#                         |___/                     #
#####################################################

def my_dash(f):
    return require_auth(require_bot_admin(server_check(f)))

def plugin_method(f):
    return my_dash(f)

def plugin_page(plugin_name):
    def decorator(f):
        @require_auth
        @require_bot_admin
        @server_check
        @wraps(f)
        def wrapper(server_id):
            user = get_user(session['api_token'])
            disable = request.args.get('disable')
            if disable:
                db.hdel('{}:Config:Cogs'.format(server_id), plugin_name)
                db.hdel("{}:Config:Delete_MSG".format(server_id),plugin_name)
                db.hincrby("Info:Cogs_Enables",plugin_name,amount=-1)
                return redirect(url_for('dashboard', server_id=server_id))
            db.hset('{}:Config:Cogs'.format(server_id), plugin_name,"on")
            db.hset("{}:Config:Delete_MSG".format(server_id),plugin_name,None)
            db.hincrby('Info:Cogs_Enables',plugin_name,amount=1)
            servers = get_user_guilds(session['api_token'])
            server = list(filter(lambda g: g['id']==str(server_id), servers))[0]
            get_plugins = db.hgetall('{}:Config:Cogs'.format(server_id))
            check_plugins = []
            for key in get_plugins:
                if get_plugins[key] == "on":
                    check_plugins.append(key)
            enabled_plugins = set(check_plugins)
            return render_template(
                f.__name__.replace('_', '-') + '.html',
                server=server,
                enabled_plugins=enabled_plugins,
                **f(server_id)
            )
        return wrapper

    return decorator

@app.route('/dashboard/<int:server_id>')
@require_auth
@require_bot_admin
@server_check
def dashboard(server_id):
    user = get_user(session['api_token'])
    guilds = get_user_guilds(session['api_token'])
    server = list(filter(lambda g: g['id']==str(server_id), guilds))[0]
    get_plugins = db.hgetall('{}:Config:Cogs'.format(server_id))
    check_plugins = []
    for key in get_plugins:
        if get_plugins[key] == "on":
            check_plugins.append(key)
    enabled_plugins = set(check_plugins)
    return render_template('dashboard.html', server=server, enabled_plugins=enabled_plugins)

#Core
@app.route('/dashboard/core/<int:server_id>')
@my_dash
def core(server_id): #UNQIUE SETTING FOR SERVER
    server = {
        'id':server_id,
        'name':db.get("{}:Level:Server_Name".format(server_id)),
        'icon':db.get("{}:Level:Server_Icon".format(server_id))
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
@plugin_method
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

#Anime
@app.route('/dashboard/<int:server_id>/myanimelist')
@plugin_page('myanimelist')
def plugin_myanimelist(server_id):
    number =random.randint(0,len(anime_picture)-1)
    return {"Info":anime_picture[number]}

#Weather
@app.route('/dashboard/<int:server_id>/weather')
@plugin_page('weather')
def plugin_weather(server_id):
    return {}

#Welcome message
@app.route('/dashboard/<int:server_id>/welcome')
@plugin_page('welcome')
def plugin_welcome(server_id):
    default_message = "{user}, welcome to **{server}**!"
    get_message = db.hget("{}:Welcome:Message".format(server_id),"message")
    if get_message is None:
        db.hset("{}:Welcome:Message".format(server_id),"message",default_message)
        get_message=default_message
    config = db.hgetall("{}:Welcome:Message".format(server_id))
    get_channel = resource_get("/guilds/{}/channels".format(server_id))
    channel = list(filter(lambda c: c['type']!='voice',get_channel))
    delete_msg = db.hget("{}:Welcome:Message".format(server_id),"delete_msg") or 0
    if config.get("channel",False) is False:
        welcome_channel=server_id
    else:
        welcome_channel = config['channel']

    db_assign_role = db.smembers('{}:Welcome:Assign_Roles'.format(server_id)) or []
    get_role = resource_get("/guilds/{}".format(server_id))
    guild_roles = get_role['roles']
    assign_role = list(filter(lambda r:r['name'] in db_assign_role or r['id'] in db_assign_role,guild_roles))
    print(get_role)
    print(guild_roles)
    return {
        'guild_channel':channel,
        "welcome_channel":welcome_channel,
        'assign_role': assign_role,
        'guild_roles':guild_roles,
        'message':get_message,
        'config':config,
        'delete_msg':delete_msg
    }

@app.route('/dashboard/<int:server_id>/welcome/update', methods=['POST'])
@plugin_method
def update_welcome(server_id):
    welcome_message = request.form.get('message')
    channel = request.form.get('channel')
    whisper_options = request.form.get('whisper')
    role_options = request.form.get("role")
    role_id = request.form.get("assign_role").split(',')
    delete_msg=request.form.get('delete_msg')
    delete_options = request.form.get("enable_delete")
    if len(welcome_message) >= 2000 or welcome_message == "":
        flash("The welcome message need to be between 1-2000!",'warning')
    else:
        try:
            delete_msg = int(delete_msg)
            print(delete_msg)
        except ValueError:
            flash('The delete message that you provided isn\'t an integer!', 'warning')
            return redirect(url_for('plugin_welcome', server_id=server_id))
        db.hset('{}:Welcome:Message'.format(server_id),'message',welcome_message)
        db.hset('{}:Welcome:Message'.format(server_id),'channel',channel)
        db.hset('{}:Welcome:Message'.format(server_id),'whisper',whisper_options)
        db.hset('{}:Welcome:Message'.format(server_id),'delete_msg',delete_msg)
        db.hset('{}:Welcome:Message'.format(server_id),'enable_delete',delete_options)
        flash('Settings updated!', 'success')
    db.hset('{}:Welcome:Message'.format(server_id),'role',role_options)
    db.delete("{}:Welcome:Assign_role".format(server_id))
    if len(role_id)>0:
        db.sadd("{}:Welcome:Assign_Roles".format(server_id),*role_id)
    return redirect(url_for('plugin_welcome', server_id=server_id))

#Discourse
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


@app.route('/dashboard/<int:server_id>/discourse')
@plugin_page('discourse')
def plugin_discourse(server_id):
    config = db.hgetall("{}:Discourse:Config".format(server_id))
    get_channel = resource_get("/guilds/{}/channels".format(server_id))
    channel = list(filter(lambda c: c['type']!='voice',get_channel))
    if config.get("channel",False) is False:
        discourse_channel=server_id
    else:
        discourse_channel = config['channel']
    return {
        'guild_channel':channel,
        "discourse_channel":discourse_channel,
        'config':config
    }

@app.route('/dashboard/<int:server_id>/discourse/update',methods=['POST'])
@plugin_method
def update_discourse(server_id):
    domain = request.form.get('domain')
    api_key=request.form.get('api_key')
    username=request.form.get('username')
    channel=request.form.get('channel')
    if len(domain) == 0 or len(api_key) == 0 or len(username) == 0:
        flash ("One of them need to be filled!",'warning')
    else:

        db.hset("{}:Discourse:Config".format(server_id),"domain",domain.strip("/"))
        db.hset("{}:Discourse:Config".format(server_id),"api_key",api_key)
        db.hset("{}:Discourse:Config".format(server_id),"username",username)
        db.hset("{}:Discourse:Config".format(server_id),"channel",channel)
        currently_topic=discourse(domain,api_key,username)
        if currently_topic is None:
            flash("There seem to be problem, please double check with domain,api key or username",'warning')
        else:
            db.set("{}:Discourse:ID".format(server_id),currently_topic)
            flash('Settings updated!', 'success')
        return redirect(url_for('plugin_discourse',server_id=server_id))

#Channel
@app.route("/dashboard/<int:server_id>/channel")
@plugin_page('channel')
def plugin_channel(server_id):
    config = db.hgetall("{}:Channel:Config".format(server_id))

    db_admin_role = db.smembers('{}:Channel:admin_roles'.format(server_id)) or []
    db_user_roles = db.smembers('{}:Channel:user_roles'.format(server_id)) or []
    get_role = resource_get("/guilds/{}".format(server_id))
    guild_roles = get_role['roles']
    admin_role = list(filter(lambda r:r['name'] in db_admin_role or r['id'] in db_admin_role,guild_roles))
    user_role = list(filter(lambda r: r['name'] in db_user_roles or r['id'] in db_user_roles,guild_roles))
    time = db.hget('{}:Channel:Config'.format(server_id),"time") or 0
    limit = db.hget('{}:Channel:Config'.format(server_id),"limit") or 0
    warning = db.hget("{}:Channel:Config".format(server_id),"warning") or 0
    print(get_role)
    print(guild_roles)
    print(admin_role)
    return {
        'config':config,
        'admin_roles': admin_role,
        'user_roles': user_role,
        'guild_roles':guild_roles,
        'time': time,
        'limit':limit,
        'warning':warning
    }

@app.route('/dashboard/<int:server_id>/channel/update',methods=['POST'])
@plugin_method
def update_channel(server_id):
    time = request.form.get('time')
    limit = request.form.get("limit")
    warning = request.form.get("warning")
    admin_roles = request.form.get('admin_roles').split(',')
    user_roles = request.form.get('user_roles').split(',')
    print(time)
    print(limit)
    print(warning)
    print(admin_roles)
    print(user_roles)
    try:
        time = int(time)
    except ValueError:
        flash('The time that you provided isn\'t an integer!', 'warning')
        return redirect(url_for('plugin_channel', server_id=server_id))
    try:
        limit = int(limit)
    except ValueError:
        flash('The limit for channel that you provided isn\'t an integer!', 'warning')
        return redirect(url_for('plugin_channel', server_id=server_id))
    try:
        warning = int(warning)
    except ValueError:
        flash('The warning for channel that you provided isn\'t an integer!', 'warning')
        return redirect(url_for('plugin_channel', server_id=server_id))

    db.hmset("{}:Channel:Config".format(server_id),{"time":time,"limit":limit,"warning":warning})
    db.delete("{}:Channel:admin_roles".format(server_id))
    if len(admin_roles)>0:
        db.sadd("{}:Channel:admin_roles".format(server_id),*admin_roles)
    db.delete("{}:Channel:user_roles".format(server_id))
    if len(user_roles)>0:
        db.sadd("{}:Channel:user_roles".format(server_id),*user_roles)
    flash('Settings updated!', 'success')

    return redirect(url_for('plugin_channel',server_id=server_id))

#Mod
@app.route('/dashboard/<int:server_id>/mod')
@plugin_page('mod')
def plugin_mod(server_id):
    db_admin_role= db.smembers('{}:Mod:admin_roles'.format(server_id)) or []
    get_role = resource_get("/guilds/{}".format(server_id))
    guild_roles = get_role['roles']
    admin_role = list(filter(lambda r:r['name'] in db_admin_role or r['id'] in db_admin_role,guild_roles))
    return{"admin_roles":admin_role,"guild_roles":guild_roles}

@app.route('/dashboard/<int:server_id>/mod/update',methods=['POST'])
@plugin_method
def update_mod(server_id):
    admin_roles = request.form.get('admin_roles').split(',')
    print(admin_roles)
    db.delete("{}:Mod:admin_roles".format(server_id))
    if len(admin_roles)>0:
        db.sadd("{}:Mod:admin_roles".format(server_id),*admin_roles)
    return redirect(url_for('plugin_mod',server_id=server_id))

@app.route('/dashboard/<int:server_id>/log')
@plugin_page('log')
def plugin_log(server_id):
    config = db.hgetall("{}:Log:Config".format(server_id))
    get_channel = resource_get("/guilds/{}/channels".format(server_id))
    channel = list(filter(lambda c: c['type']!='voice',get_channel))
    if config.get("channel",False) is False:
        log_channel=server_id
    else:
        log_channel = config['channel']
    return {
        'guild_channel':channel,
        "log_channel":log_channel,
        'config':config
    }

@app.route('/dashboard/<int:server_id>/log/update',methods=['POST'])
@plugin_method
def update_log(server_id):
    list_point = dict(request.form)
    list_point.pop('_csrf_token',None)
    path = "{}:Log:Config".format(server_id)
    log_bool = False
    db.delete(path)
    for x in list_point:
        if request.form.get(x):
            log_bool = True
        print("{} is {}".format(x,request.form.get(x)))
        db.hset(path,x,request.form.get(x))
    if log_bool:
        db.sadd("Info:Log",server_id)
    flash('Settings updated!', 'success')
    return redirect(url_for('plugin_log', server_id=server_id))


#Level
@app.route('/dashboard/<int:server_id>/levels')
@plugin_page('level')
def plugin_levels(server_id):
    initial_announcement = '{player}, you just advanced to **level {level}** !\n Now go and fight more mob!'
    announcement = db.hget('{}:Level:Config'.format(server_id),"announce_message")
    if announcement is None:
        db.hset('{}:Level:Config'.format(server_id),"announce_message", initial_announcement)
        db.hset('{}:Level:Config'.format(server_id),"announce",'on')
    config = db.hgetall("{}:Level:Config".format(server_id))

    db_banned_members = db.smembers('{}:Level:banned_members'.format(server_id)) or []
    db_banned_roles = db.smembers('{}:Level:banned_roles'.format(server_id)) or []
    get_role = resource_get("/guilds/{}".format(server_id))
    guild_roles = get_role['roles']
    get_member = resource_get("/guilds/{}/members?&limit=1000".format(server_id))
    guild_members=[]
    for x in get_member:
        guild_members.append(x['user'])
    banned_roles = list(filter(lambda r: r['name'] in db_banned_roles or r['id'] in db_banned_roles,guild_roles))
    banned_members = list(filter(lambda r:r['username'] in db_banned_members or r['id'] in db_banned_members,guild_members))
    cooldown = db.hget('{}:Level:Config'.format(server_id),"rank_cooldown") or 0
    print(guild_roles)
    return {
        'config':config,
        'banned_members': banned_members,
        'guild_members':guild_members,
        'banned_roles': banned_roles,
        'guild_roles':guild_roles,
        'cooldown': cooldown,
    }

@app.route('/dashboard/<int:server_id>/levels/update', methods=['POST'])
@plugin_method
def update_levels(server_id):
    servers = get_user_guilds(session['api_token'])
    server = list(filter(lambda g: g['id']==str(server_id),servers))[0]

    banned_members = request.form.get('banned_members').split(',')
    banned_roles = request.form.get('banned_roles').split(',')
    announcement = request.form.get('announcement')
    enable = request.form.get('enable')
    whisp = request.form.get('whisp')
    delete_msg = request.form.get('delete_msg')
    print(banned_roles)
    cooldown = request.form.get('cooldown')
    print("ENABLE IS {}".format(enable))
    print("WHISPER IS  {}".format(whisp))
    print("DELETE MESG IS {}".format(delete_msg))
    try:
        cooldown = int(cooldown)
    except ValueError:
        flash('The cooldown that you provided isn\'t an integer!', 'warning')
        return redirect(url_for('plugin_levels', server_id=server_id))

    if announcement == '' or len(announcement) > 2000:
        flash('The level up announcement could not be empty or have 2000+ characters.', 'warning')
    else:
        db.hset('{}:Level:Config'.format(server_id),"announce_message", announcement)
        db.hset('{}:Level:Config'.format(server_id),"rank_cooldown", cooldown)

        db.delete('{}:Level:banned_members'.format(server_id))
        if len(banned_members)>0:
            db.sadd('{}:Level:banned_members'.format(server_id), *banned_members)

        db.delete('{}:Level:banned_roles'.format(server_id))
        if len(banned_roles)>0:
            db.sadd('{}:Level:banned_roles'.format(server_id), *banned_roles)

        db.hset('{}:Level:Config'.format(server_id),"announce", enable)

        db.hset('{}:Level:Config'.format(server_id),"whisper", whisp)

        flash('Settings updated!', 'success')

    return redirect(url_for('plugin_levels', server_id=server_id))

@app.route('/levels/<int:server_id>')
def levels(server_id):
    is_admin = False
    if session.get('api_token'):
        user_servers = get_user_managed_servers(
            get_user(session['api_token']),
            get_user_guilds(session['api_token'])
        )
        is_admin = str(server_id) in list(map(lambda s:s['id'], user_servers))
    is_private=False
    if db.get("{}:Level:Private".format(server_id)) == "on":
        is_private=True
    print(is_private)
    #Check if server and plugins are in
    server_check = db.hget("Info:Server",server_id)
    if server_check is None:
        return redirect(url_for('index'))
    plugin_check = db.hget("{}:Config:Cogs".format(server_id),"level")
    if plugin_check is None:
        return redirect(url_for('index'))

    server = {
        'id':server_id,
        'name':server_check,
        'icon':db.hget("Info:Server_Icon",server_id)
    }
    name_list = db.hgetall("Info:Name")
    print(name_list)
    avatar_list = db.hgetall("Info:Icon")
    print(avatar_list)
    total_member = len(db.smembers("{}:Level:Player".format(server_id)))
    player_data = db.sort("{}:Level:Player".format(server_id), by="{}:Level:Player:*->Total_XP".format(server_id), get=[
                                                                                                          "{}:Level:Player:*->Name".format(server_id),
                                                                                                          "{}:Level:Player:*->ID".format(server_id),
                                                                                                          "{}:Level:Player:*->Level".format(server_id),
                                                                                                          "{}:Level:Player:*->XP".format(server_id),
                                                                                                          "{}:Level:Player:*->Next_XP".format(server_id),
                                                                                                          "{}:Level:Player:*->Total_XP".format(server_id),
                                                                                                          "{}:Level:Player:*->Discriminator".format(server_id)], start=0, num=total_member, desc=True)
    data = []
    for x in range(0,len(player_data),7):
            if name_list.get(player_data[x+1]) is False:
                db.srem("{}:Level:Player".format(server_id),player_data[x+1])
            temp = {
                "Name":player_data[x],
                "ID":player_data[x+1],
                "Level":player_data[x+2],
                "XP":player_data[x+3],
                "Next_XP":player_data[x+4],
                "Total_XP":player_data[x+5],
                "Discriminator":player_data[x+6],
                "Avatar":avatar_list.get(player_data[x+1],None),
                "XP_Percent":100*(float(player_data[x+3])/float(player_data[x+4]))
            }
            data.append(temp)
        #Those are for Website
    return render_template('levels.html', players=data, server=server, title="{} leaderboard".format(server['name']),is_admin=is_admin,is_private=is_private)

@app.route('/server/levels')
def server_levels():
    server_list=db.hgetall("Info:Server")
    server_icon=db.hgetall("Info:Server_Icon")
    enable_level= []
    for server_id in server_list:#run a loops of server list
        if db.hget("{}:Config:Cogs".format(server_id),"level") == "on": #IF this plugins is on, then it will collect data
            if db.get("{}:Level:Private".format(server_id)):
                continue
            else:
                player_total=[]
                for player_id in db.smembers("{}:Level:Player".format(server_id)): #Get every player's total XP
                    try:
                        player_total.append(int(db.hget("{}:Level:Player:{}".format(server_id,player_id),"Total_XP")))
                    except:

                        continue
                total = sum(player_total)
                print("{}-{} total xp is {}".format(server_id,server_list[server_id],total))
                try:
                    level = int(math.log(total/100,3))
                except:
                    level = 0
                next_xp = int(100*3**(level+1))
                enable_level.append([server_list[server_id],server_icon.get(server_id),server_id,
                                     total,next_xp,(100*(float(total)/float(next_xp))),level])
    enable_level=sorted(enable_level,key=lambda enable_level:enable_level[4],reverse=True)
    return render_template('server_level.html',title="Server Leaderboard",server_list=enable_level)

@app.route('/levels/reset/<int:server_id>/<int:player_id>')
@plugin_method
def reset_player(server_id, player_id):
    db.delete('{}:Level:Player:{}'.format(server_id, player_id))
    db.srem('{}:Level:Player'.format(server_id), player_id)
    return redirect(url_for('levels', server_id=server_id))

@app.route('/levels/reset_all/<int:server_id>')
@plugin_method
def reset_all_players(server_id):
    for player_id in db.smembers('{}:Level:Player'.format(server_id)):
        db.delete('{}:Level:Player:{}'.format(server_id, player_id))
        db.srem('{}:Level:Player'.format(server_id), player_id)
    return redirect(url_for('levels', server_id=server_id))

@app.route('/levels/private_set/<int:server_id>/<int:bool>')
@plugin_method
def private_server(server_id,bool):
    print(bool)
    print("Update private server")
    if bool == 1: #set it as private
        db.set("{}:Level:Private".format(server_id),"on")
    else:
        db.delete("{}:Level:Private".format(server_id))
    return redirect(url_for('levels', server_id=server_id))

@app.route('/profile/private_set/<int:player_id>/<int:server_id>/<int:bool>')
@plugin_method
def private_profile(server_id,player_id,bool):
    print("okay")
    print(bool)
    if bool == 1:
        db.sadd("{}:Level:Player:Private".format(server_id),player_id)
        print("add!")
    else:
        print("remove")
        db.srem("{}:Level:Player:Private".format(server_id),player_id)
    return redirect(url_for('profile', server_id=server_id,player_id=player_id))

@app.route('/profile/level/<string:player_id>/<int:server_id>')
def profile_level(player_id,server_id):
    #Checking if is owner of that site
    is_owner = False
    if session.get('api_token'):
        user_id =get_user(session['api_token'])['id']

        is_owner = str(player_id) == str(user_id)
    # is_private=False #checking if page is private or not.
    is_private=player_id in db.smembers("{}:Level:Player:Private".format(server_id))
    # print(player_id in db.smembers("{}:Level:Player:Private".format(server_id)))
    # for id in db.smembers("{}:Level:Player:Private".format(server_id)):
    #     if player_id == id:
    #         is_private=True
    # print(is_private)
    server = {
    'id':server_id,
    'name':db.get("{}:Level:Server_Name".format(server_id)),
    'icon':db.get("{}:Level:Server_Icon".format(server_id))
    }
    xp=0
    data_temp = db.hgetall("{}:Total_Command:{}".format(server_id,player_id))
    level =db.hgetall("{}:Level:Player:{}".format(server_id,player_id))
    if len(level) > 0:
        xp = 100*float(float(level["XP"])/float(level["Next_XP"]))
        level.update({"Percents":int(xp)})
    else:
        level=None
    if len(data_temp) == 0:
        data =None
    else:
        data_array = [(i,data_temp[i])for i in data_temp]
        data_array.sort(key=lambda x: int(x[1]),reverse=True)
        data = []
        for x,y in data_array:
            data.append("{} - {}".format(x,y))
    icon = db.hget("Info:Icon",player_id)
    name = db.hget("Info:Name",player_id)
    return render_template("profile_level.html",data=data,icon=icon,name=name,player_id=player_id,
                           server=server,level=level,XP_Percent=xp,title="{} Profile".format(name),
                           is_owner=is_owner,is_private=is_private)

@app.before_first_request
def setup_logging():
    # In production mode, add log handler to sys.stderr.
    app.logger.addHandler(logging.StreamHandler())
    app.logger.setLevel(logging.INFO)

@app.errorhandler(401)
def page_not_found(e):
    #if there is error with 401, it would redirect you to login pages
    #It happen when you login in other area other than your site.
    return redirect("/login")

if __name__=='__main__':
    app.debug = True
    app.run()