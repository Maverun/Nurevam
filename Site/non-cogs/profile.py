from flask import Blueprint, render_template, request, redirect, url_for, flash,session
import requests
import logging
import utils

log = logging.getLogger("Nurevam.site")

blueprint = Blueprint('profile', __name__, template_folder='../templates/profile')

db = None  #Database

osu_api = None

@blueprint.route('/profile')
@utils.require_auth
def profile():
    """
    A user profile.
    It's purpose is for globals setting across server.
    """
    user = session['user']
    setting = db.hgetall("Profile:{}".format(user["id"]))
    return render_template('profile.html',user=user,setting=setting)

@blueprint.route('/profile/update', methods=['POST'])
@utils.require_auth
def update_profile(): #Update a setting.
    list_point = dict(request.form)
    list_point.pop('_csrf_token',None)
    path = "Profile:{}".format(session['user']['id'])
    warning = False
    warning_msg = "One of those have failed, Please double check {} "
    warning_list =[]
    for  x in list_point:
        if request.form.get(x) == "":
            db.hdel(path,x)
            continue
        if x == "myanimelist":
            status = status_site("http://myanimelist.net/profile/{}".format(request.form.get(x)))
            if status is False:
                warning = True
                warning_list.append(x)
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
    return redirect(url_for('profile'))

def status_site(site):
    r = requests.get(site)
    if r.status_code == 200:
        return True
    else:
        return False

