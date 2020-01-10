from flask import session,redirect,url_for,request,render_template,abort,current_app,flash
from requests_oauthlib import OAuth2Session
from functools import wraps
import requests
import logging
import json
import time

log = logging.getLogger('Nurevam.site')

db = None
data_info = None
def is_owner():
    if session["user"]["id"] == "105853969175212032":
        log.info("It is dev Mave")
        return True
    return False


def my_dash(f):
    return require_auth(require_bot_admin(server_check(f)))

def plugin_method(f):
    return my_dash(f)

def require_auth(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        # Does the user have an api_token?
        api_token = session.get('api_token')
        if api_token is None:
            log.info("No api token, redirect to login")
            return redirect(url_for('login'))

        # Does his api_key is in the db?
        user_api_key = db.get('user:{}:api_key'.format(api_token['user_id']))
        if user_api_key != api_token['api_key']:
            log.info("API key dont match, refresh them")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrapper

def require_bot_admin(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if is_owner(): return f(*args,**kwargs)
        server_id = kwargs.get('server_id')
        user = get_user(session['api_token'])
        guilds = get_user_guilds(session['api_token'])
        user_servers = get_user_managed_servers(user, guilds)
        if str(server_id) not in map(lambda g: g['id'], user_servers):
            log.info("Not admin")
            return redirect(url_for('select_server'))
        log.info("Complete Admin")
        return f(*args, **kwargs)
    return wrapper

def server_check(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        server_id = kwargs.get('server_id')
        server_ids = db.hget("Info:Server",server_id)

        if server_ids is None:
            url =   "https://discordapp.com/oauth2/authorize?&client_id={}"\
                    "&scope=bot&permissions={}&guild_id={}&response_type=code"\
                    "&redirect_uri=http://{}/servers".format(data_info.OAUTH2_CLIENT_ID,'66321471',server_id,data_info.DOMAIN)
            return redirect(url)
        return f(*args, **kwargs)
    return wrapper

def require_role(f):
    @require_auth
    @wraps(f)
    def wrapper(*args,**kwargs):
        if is_owner(): return f(*args,**kwargs)
        cog = kwargs.get("cog").title()
        server_id = kwargs.get("server_id")
        user = session.get('user')
        get_user_role = resource_get("/guilds/{}/members/{}".format(server_id,user['id']))
        editor_role = db.smembers("{}:{}:editor_role".format(server_id,cog))
        for x in editor_role:
            if x in get_user_role["roles"]:
                return f(*args, **kwargs)
        return redirect(url_for('index'))
    return wrapper

def plugin_page(plugin_name):
    def decorator(f):
        @require_auth
        @require_bot_admin
        @server_check
        @wraps(f)
        def wrapper(server_id):
            # user = get_user(session['api_token'])
            disable = request.args.get('disable')
            log.info("the dashboard disable is {} {}".format(disable,plugin_name))
            if disable:
                log.info("Disable plugins, {} for {}".format(plugin_name,server_id))
                db.hdel('{}:Config:Cogs'.format(server_id), plugin_name)
                db.hdel("{}:Config:Delete_MSG".format(server_id),plugin_name)
                return redirect(url_for('dashboard', server_id=server_id))

            db.hset('{}:Config:Cogs'.format(server_id), plugin_name,"on")
            db.hset("{}:Config:Delete_MSG".format(server_id),plugin_name,None)

            icon = db.hget("Info:Server_Icon", server_id)
            name = db.hget("Info:Server", server_id)

            get_enable_list = db.hgetall("{}:Config:Cogs".format(server_id))
            info = [[key, values.name.title(), values.description] for key, values in current_app.blueprint_lib.items()]
            enable_plugin = [x for x in current_app.blueprint_lib if x in get_enable_list]
            info.sort(key=lambda x:x[1])
            return render_template("/{}/index.html".format(plugin_name),
                server={"id": server_id, "icon": icon, "name": name},
                info = info,
                enable_plugin=enable_plugin,
                **f(server_id))
        return wrapper

    return decorator

def resource_get(end):#Getting a resournces from API
    r = requests.get(data_info.API_BASE_URL+end,headers=data_info.headers)
    if r.status_code == 200:
        return r.json()
    return None

"""
    Discord DATA logic
"""

def get_user(token):
    # If it's an api_token, go fetch the discord_token
    user_id = None
    if token.get('api_key'):
        user_id = token['user_id']
        discord_token_str = db.get('user:{}:discord_token'.format(token['user_id']))
        token = json.loads(discord_token_str)

    discord = make_session(token=token)
    #Checking cache exists
    if user_id:
        user_cache = db.get('user:{}'.format(user_id))
        if user_cache:
            return json.loads(user_cache)

    req = discord.get(data_info.API_BASE_URL + '/users/@me')
    if req.status_code != 200:
        abort(req.status_code)

    user = req.json()
    # Saving that to the session for easy template access
    session['user'] = user

    # Saving that to the db and set it expire
    db.sadd('users', user['id'])
    db.set('user:{}'.format(user['id']), json.dumps(user),ex = 30)
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
    #checking if there is cache already, if so, just return that, else we will have to make requests
    guild_cache = db.get('user:{}:guilds'.format(user_id))
    if guild_cache:
        return json.loads(guild_cache)

    #making requests to get json info
    req = discord.get(data_info.API_BASE_URL + '/users/@me/guilds')
    if req.status_code == 429: #if any, i would like to avoid this until last resort
        try:
            current = time.time()
            time.sleep(int(req.headers["X-RateLimit-Reset"])-current)
        except:
            pass
        return get_user_guilds(token) #rerun it again.
    elif req.status_code != 200:
        abort(req.status_code)

    guilds = req.json()
    # Saving that to the db and set it expire as rate limit is approx 1-2 second?
    db.set('user:{}:guilds'.format(user_id), json.dumps(guilds),ex = 30)#30 second seem to be reasonable
    return guilds

def get_user_managed_servers(user, guilds):
    return list(filter(lambda g: (g['owner'] is True) or bool(( int(g['permissions'])>> 5) & 1), guilds))

def get_channel(server_id): #Shortcut to get channel,so i dont have to remember how to do this again...
    get_channel = resource_get("/guilds/{}/channels".format(server_id))
    return list(filter(lambda c: c['type'] == 0,get_channel)) #type 0 is text channel


"""
    AUTH logic
"""

def token_updater(discord_token):
    user = get_user(discord_token)
    # Save the new discord_token
    db.set('user:{}:discord_token'.format(user['id']), json.dumps(discord_token))

def make_session(token=None, state=None, scope=None):
    return OAuth2Session(
        client_id=data_info.OAUTH2_CLIENT_ID,
        token=token,
        state=state,
        scope=scope,
        redirect_uri=data_info.OAUTH2_REDIRECT_URI,
        auto_refresh_kwargs={
            'client_id': data_info.OAUTH2_CLIENT_ID,
            'client_secret': data_info.OAUTH2_CLIENT_SECRET,
        },
        auto_refresh_url=data_info.TOKEN_URL,
        token_updater=token_updater
)

def check_link(link):
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

def is_admin(server_id):
    if session.get('api_token'):
        user_servers = get_user_managed_servers(get_user(session['api_token']),
            get_user_guilds(session['api_token']))
        return str(server_id) in list(map(lambda s:s['id'], user_servers))
    return False