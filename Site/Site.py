from flask import Flask, session, request, url_for, render_template, redirect, \
jsonify, make_response, flash, abort, Response
import os
from functools import wraps
from requests_oauthlib import OAuth2Session
import redis
import binascii


db = redis.Redis(host='localhost',decode_responses=True,db=2)

app = Flask(__name__)


# CSRF
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

def token_updater(token):
    session['oauth2_token'] = token

def require_auth(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        user = session.get('user')
        if user is None:
            return redirect(url_for('login'))

        return f(*args, **kwargs)
    return wrapper

def make_session(token=None, state=None, scope=None):
    pass
    return OAuth2Session( #Need to work on this soon ASAP.
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
        token_updater=token_updater)

@app.route('/')
def index():
    return render_template('index.html')
@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/logout')
def logout():
    session.pop('user')

    return redirect(url_for('index'))
@app.route('/login')
def login():
    user = session.get('user')
    if user is not None:
        return redirect(url_for('select_server'))

    scope = 'identify guilds'.split()
    discord = make_session(scope=scope)
    authorization_url, state = discord.authorization_url(AUTHORIZATION_BASE_URL)
    session['oauth2_state'] = state
    return redirect(authorization_url)

@app.route('/levels/<int:server_ID>')
def level(server_ID):
    print(server_ID)
    server = {
        'id':server_ID,
        'name':db.get("{}:Level:Server_Name".format(server_ID)),
        'icon':db.get("{}:Level:Server_Icon".format(server_ID))
    }
    player_data = db.sort("{}:Level:Player".format(server_ID), by="{}:Level:Player:*->Total_XP".format(server_ID), get=[
                                                                                                          "{}:Level:Player:*->Name".format(server_ID),
                                                                                                          "{}:Level:Player:*->ID".format(server_ID),
                                                                                                          "{}:Level:Player:*->Level".format(server_ID),
                                                                                                          "{}:Level:Player:*->XP".format(server_ID),
                                                                                                          "{}:Level:Player:*->Next_XP".format(server_ID),
                                                                                                          "{}:Level:Player:*->Total_XP".format(server_ID),
                                                                                                          "{}:Level:Player:*->Discriminator".format(server_ID),
                                                                                                          "{}:Level:Player:*->Avatar".format(server_ID),
                                                                                                          "{}:Level:Player:*->Total_Traits_Points"], start=0, num=10, desc=True)
    data = []
    for x in range(0,len(player_data),9):
        temp = {
            "Name":player_data[x],
            "ID":player_data[x+1],
            "Level":player_data[x+2],
            "XP":player_data[x+3],
            "Next_XP":player_data[x+4],
            "Total_XP":player_data[x+5],
            "Discriminator":player_data[x+6],
            "Avatar":player_data[x+7],
            "Total_Traits":player_data[x+8],
            "XP_Percent":100*(float(player_data[x+3])/float(player_data[x+4]))
        }
        data.append(temp)
        #Those are for Website
    return render_template('levels.html', players=data, server=server, title="{} leaderboard - Mee6 bot".format(server['name']))


if __name__=='__main__':
    app.debug = True
    app.run()