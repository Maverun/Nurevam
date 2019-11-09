from flask import Blueprint, render_template, request, redirect, url_for, flash,session
# from pyanimu import Anilist,UserStatus_Anilist, connectors
from requests_oauthlib import OAuth2Session
import requests
import logging
import utils

log = logging.getLogger("Nurevam.site")

blueprint = Blueprint('profile', __name__, template_folder='../templates/profile')

db = None  #Database

osu_api = None

@blueprint.route('/')
@utils.require_auth
def profile():
    """
    A user profile.
    It's purpose is for globals setting across server.
    """
    user = session['user']
    setting = db.hgetall("Profile:{}".format(user["id"]))
    return render_template('profile.html',user=user,setting=setting,anilist_cleint_id = utils.data_info.anilist_id,anilist_redirect = url_for('profile.anilist_request',_external=True))

@blueprint.route('/update', methods=['POST'])
@utils.require_auth
def update_profile(): #Update a setting.
    list_point = dict(request.form)
    list_point.pop('_csrf_token',None)
    path = "Profile:{}".format(session['user']['id'])
    warning = False
    warning_msg = "One of those have failed, Please double check {} "
    warning_list =[]
    for  x in list_point:
        print(x)
        if request.form.get(x) == "":
            db.hdel(path,x)
            continue
        elif x == "osu":
            results = osu_api.get_user(request.form.get(x))
            if results == []:
                warning = True
                warning_list.append(x)
                continue
        db.hset(path,x,request.form.get(x))
    if warning:
        flash(warning_msg.format(",".join(warning_list)), 'warning')
    else:
        flash('Settings updated!', 'success')
    return redirect(url_for('profile.profile'))

def status_site(site):
    r = requests.get(site)
    if r.status_code == 200:
        return True
    else:
        return False

@blueprint.route('/anilist/')
@utils.require_auth
def anilist_request():
    code = request.args.get("code")
    header = {'Content-Type': 'application/json','Accept': 'application/json'}
    r = requests.post("https://anilist.co/api/v2/oauth/token",json = {
        'client_id':str(utils.data_info.anilist_id),
        'client_secret':utils.data_info.anilist_token,
        'redirect_uri':url_for('profile.anilist_request',_external=True),
        'grant_type': 'authorization_code',
        'code':code},headers=header)
    data =r.json()
    user = session['user']

    db.hmset("Profile:{}:Anilist".format(user["id"]),data)
    print("Successfully create token for ",user["id"]," - ",user["username"])
    flash("Anilist update!","success")
    return redirect(url_for('profile.profile'))

