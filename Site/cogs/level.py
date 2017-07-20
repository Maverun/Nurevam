from flask import Blueprint, render_template,request,flash,redirect,url_for,jsonify,send_file
from PIL import Image,ImageFont,ImageDraw,ImageFilter
import requests
import logging
import base64
import utils
import io
import os

log = logging.getLogger("Nurevam.site")

blueprint = Blueprint('level', __name__, template_folder='../templates/level',static_folder="static")

name = "levels"
description = "Let your members gain <strong>XP</strong> and <strong> levels</strong> by participating in the chat!"

db = None  #Database

@utils.plugin_page('level')
def dashboard(server_id):
    log.info("Level dashboard")
    key_path = '{}:Level:Config'.format(server_id)
    initial_announcement = '{player}, you just advanced to **level {level}** !\n Now go and fight more mob!'
    announcement = db.hget(key_path,"announce_message")
    if announcement is None:
        db.hset(key_path,"announce_message", initial_announcement)
        db.hset(key_path.format(server_id),"announce",'on')

    cooldown = db.hget(key_path.format(server_id),"rank_cooldown") or 0
    config = db.hgetall(key_path)
    #getting database of members
    db_banned_members = db.smembers('{}:Level:banned_members'.format(server_id)) or []
    db_banned_roles = db.smembers('{}:Level:banned_roles'.format(server_id)) or []
    db_banned_channels = db.smembers('{}:Level:banned_channels'.format(server_id)) or []
    #checking roles
    get_role = utils.resource_get("/guilds/{}".format(server_id))
    guild_roles = get_role['roles']
    #get member info
    get_member = utils.resource_get("/guilds/{}/members?&limit=1000".format(server_id))
    guild_members=[x['user'] for x in get_member]
    #getting channel
    guild_channels = utils.get_channel(server_id)
    #ban role and members
    banned_roles = list(filter(lambda r: r['id'] in db_banned_roles,guild_roles))
    banned_members = list(filter(lambda r:r['id'] in db_banned_members,guild_members))
    banned_channels = list(filter(lambda r:r['id'] in db_banned_channels,guild_channels))
    log.info("Done getting list of banned, now getting rewards roles")
    #reward roles
    role_level = db.hgetall("{}:Level:role_reward".format(server_id)) or {}
    temp = [
        {"name":x['name'],
         "id":x['id'],
         "color":hex(x["color"]).split("0x")[1],
         "level":role_level.get(x["id"],0)} for x in guild_roles]
    temp.sort(key=lambda x: x['name'])

    reward_roles = [temp[:int(len(temp)/2)],temp[int(len(temp)/2):]] #Spliting them into half

    return {
        'config':config,
        'banned_members': banned_members,
        'guild_members':guild_members,
        'banned_roles': banned_roles,
        'guild_roles':guild_roles,
        'banned_channels':banned_channels,
        'guild_channels':guild_channels,
        'cooldown': cooldown,
        "reward_roles":reward_roles,
        }

@blueprint.route('/update/<int:server_id>', methods=['POST'])
@utils.plugin_method
def update_levels(server_id):
    log.info(request.form)
    data = dict(request.form)
    banned_members = data.pop('banned_members')[0].split(',')
    banned_roles = data.pop('banned_roles')[0].split(',')
    banned_channels = data.pop('banned_channels')[0].split(',')
    announcement = data.pop('announcement')[0]
    enable = data.pop('enable',None)
    whisp = data.pop('whisp',None)
    cooldown = data.pop('cooldown',[0])[0]
    data.pop("_csrf_token") #removing it so we can focus on role reward easily
    try:
        cooldown = int(cooldown)
    except ValueError:
        flash('The cooldown that you provided isn\'t an integer!', 'warning')
        return dashboard(server_id=server_id)

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

        db.delete('{}:Level:banned_channels'.format(server_id))
        if len(banned_roles)>0:
            db.sadd('{}:Level:banned_channels'.format(server_id), *banned_channels)

        db.hset('{}:Level:Config'.format(server_id),"announce", enable)

        db.hset('{}:Level:Config'.format(server_id),"whisper", whisp)
        role_reward = {}
        for key,values in data.items():
            if "level_role" in key:
                key = key.strip("level_role")
                if values[0].isdigit():
                    role_reward[key] = values[0]
                else:
                    flash("Role must be only having integer number!".format(key),"warning")
                    return dashboard(server_id = server_id)
        db.hmset("{}:Level:role_reward".format(server_id),role_reward)
        flash('Settings updated!', 'success')
    log.info("Clear")
    return dashboard(server_id = server_id)

def next_Level(xp,lvl=0,x=2):
    f = 2*(lvl**x)+20*(lvl)+100
    if xp >= f:
        return next_Level(xp-f,lvl+1,x)
    return lvl,xp,f

@blueprint.route('/<int:server_id>')
def levels(server_id):
    is_admin = utils.is_admin(server_id)
    css_theme  = "css/custom/{}.css".format(server_id) if os.path.isfile("static/css/custom/{}.css".format(server_id)) else None
    print(css_theme)
    is_private=False
    if db.get("{}:Level:Private".format(server_id)) == "on":
        is_private=True
    #Check if server and plugins are in
    server_check = db.hget("Info:Server",server_id)
    if server_check is None:
        return redirect(url_for('index'))
    plugin_check = db.hget("{}:Config:Cogs".format(server_id),"level")
    if plugin_check is None:
        return redirect(url_for('index'))

    log.info("Pass all requirement check")

    server = {
        'id':server_id,
        'name':server_check,
        'icon':db.hget("Info:Server_Icon",server_id)}

    #Players' level
    name_list = db.hgetall("Info:Name")
    avatar_list = db.hgetall("Info:Icon")
    total_member = len(db.smembers("{}:Level:Player".format(server_id)))
    player_data = db.sort("{}:Level:Player".format(server_id), by="{}:Level:Player:*->Total_XP".format(server_id), get=[
                                                                                                          "{}:Level:Player:*->ID".format(server_id),
                                                                                                          "{}:Level:Player:*->Total_XP".format(server_id),], start=0, num=total_member, desc=True)
    data = []
    total_exp = 0
    for x in range(0,len(player_data),2):

            if name_list.get(player_data[x]) is None:
                db.srem("{}:Level:Player".format(server_id),player_data[x])
            if player_data[x] is None: continue
            # print(player_data[x],player_data[x+1]) #for future references
            total_exp += int(player_data[x+1])
            level, remain,next_xp= next_Level(int(player_data[x+1]))
            name = name_list.get(player_data[x],"None#1234").split("#")
            temp = {
                "Name":name[0],
                "ID":player_data[x],
                "Level":level,
                "XP": remain,
                "Next_XP":next_xp,
                "Total_XP":player_data[x+1],
                "Discriminator":name[1],
                "Avatar":avatar_list.get(player_data[x]),
                "XP_Percent":100*(float(remain)/float(next_xp))
            }
            data.append(temp)
    log.info("Done gather player infos")
    #Role rewards
    get_role = utils.resource_get("/guilds/{}".format(server_id))
    guild_roles = get_role['roles']
    role_level = db.hgetall("{}:Level:role_reward".format(server_id)) or {}
    reward_roles = [
        {"name":x['name'],
         "id":x['id'],
         "color":hex(x["color"]).split("0x")[1],
         "level":role_level.get(x["id"],0)} for x in guild_roles if role_level.get(x["id"],"0") != "0" and x["id"] != str(server_id)]
    reward_roles.sort(key=lambda x: x['name'])
    print(reward_roles)
    #Those are for Website
    stats = {"total_member":total_member,"total_exp":total_exp}

    if request.args.get('json'):
        log.info("Requesting Json")
        return jsonify({"server:":server,"reward_roles":reward_roles,"players":data})

    return render_template('level/levels.html', players=data, stats = stats, reward_roles = reward_roles,server=server, title="{} leaderboard".format(server['name']),is_admin=is_admin,is_private=is_private,css_theme = css_theme)

@blueprint.route('/server')
def server_levels():
    server_list=db.hgetall("Info:Server")
    server_icon=db.hgetall("Info:Server_Icon")
    enable_level= []
    for server_id in server_list:#run a loops of server list
        if db.hget("{}:Config:Cogs".format(server_id),"level") == "on": #IF this plugins_html is on, then it will collect data
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
                level,remain,next_xp = next_Level(total,x = 5)
                print("{}-{} total xp is {},xp: {} remain is {}".format(server_id,server_list[server_id],total,next_xp,remain))
                enable_level.append([server_list[server_id],server_icon.get(server_id),server_id,remain,next_xp,(100*(float(remain)/float(next_xp))),level])
    log.info(enable_level)
    enable_level=sorted(enable_level,key=lambda enable_level:enable_level[4],reverse=True)
    return render_template('level/server_level.html',title="Server Leaderboard",server_list=enable_level)

@blueprint.route('/reset/<int:server_id>/<int:player_id>')
@utils.plugin_method
def reset_player(server_id, player_id):
    log.info("Reset that player's data")
    db.delete('{}:Level:Player:{}'.format(server_id, player_id))
    db.srem('{}:Level:Player'.format(server_id), player_id)
    return redirect(url_for('level.levels', server_id=server_id))

@blueprint.route('/reset_all/<int:server_id>')
@utils.plugin_method
def reset_all_players(server_id):
    log.info("Someone must be insane reset everything?")
    for player_id in db.smembers('{}:Level:Player'.format(server_id)):
        db.delete('{}:Level:Player:{}'.format(server_id, player_id))
        db.srem('{}:Level:Player'.format(server_id), player_id)
    return redirect(url_for('level.levels', server_id=server_id))

@blueprint.route('/private_set/<int:server_id>/<int:bool>')
@utils.plugin_method
def private_server(server_id,bool):
    if bool == 1: #set it as private
        db.set("{}:Level:Private".format(server_id),"on")
    else:
        db.delete("{}:Level:Private".format(server_id))
    return redirect(url_for('levels', server_id=server_id))

@blueprint.route('/profile/private_set/<int:player_id>/<int:server_id>/<int:bool>')
@utils.plugin_method
def private_profile(server_id,player_id,bool):
    if bool == 1:
        db.sadd("{}:Level:Player:Private".format(server_id),player_id)
    else:
        db.srem("{}:Level:Player:Private".format(server_id),player_id)
    return redirect(url_for('profile', server_id=server_id,player_id=player_id))

@blueprint.route('/profile/<string:player_id>/<int:server_id>')
def profile_level(player_id,server_id):
    #Checking if is owner of that site
    is_owner = False
    if utils.session.get('api_token'):
        user_id =utils.get_user(utils.session['api_token'])['id']

        is_owner = str(player_id) == str(user_id)
    is_private=player_id in db.smembers("{}:Level:Player:Private".format(server_id))
    server = {
        'id':server_id,
        'name':db.hget("Info:Server",server_id),
        'icon':db.hget("Info:Server_Icon",server_id)
    }
    print(server)
    xp=0
    data_temp = db.hgetall("{}:Total_Command:{}".format(server_id,player_id))
    level_data =db.hgetall("{}:Level:Player:{}".format(server_id,player_id))

    if len(level_data) > 0:

        level,remain,next_exp = next_Level(int(level_data["Total_XP"]))
        level_data.update({"Level":level,"Next_XP":next_exp})
        xp = 100*float(float(remain)/float(next_exp))
        level_data.update({"Percents":int(xp)})
        print(level_data)
    else:
        data = None
    #This is command used list
    if len(data_temp) == 0:
        data = None
    else:
        data_array = [(i,data_temp[i])for i in data_temp]
        data_array.sort(key=lambda x: int(x[1]),reverse=True)
        data = ["{} - {}".format(x,y) for x,y in data_array]
    #Their name and icon
    icon = db.hget("Info:Icon",player_id)
    name = db.hget("Info:Name",player_id)
    return render_template("level/profile_level.html",data=data,icon=icon,name=name,player_id=player_id,
                           server=server,level=level_data,XP_Percent=xp,title="{} Profile".format(name),
                            is_owner=is_owner,is_private=is_private)

@blueprint.route("/theme/<int:server_id>")
@utils.plugin_method
def theme(server_id):
    server = {
        'id':server_id,
        'name':db.hget("Info:Server",server_id),
        'icon':db.hget("Info:Server_Icon",server_id)}

    setting = db.hgetall("{}:Level:pic_setting".format(server_id))
    color_setting = db.hgetall("{}:Level:color".format(server_id))

    #setting color setting
    border = tuple((int(x) for x in color_setting.get("border",("255,255,255,96")).split(",")))
    row = tuple((int(x) for x in color_setting.get("row",("255,255,255,48")).split(",")))
    text = tuple((int(x) for x in color_setting.get("text",("255,255,255")).split(",")))
    outlier = tuple((int(x) for x in color_setting.get("outlier",("0,0,0")).split(",")))


    if bool(setting)is False:
        setting = {"border":"on","row":"on","outlier":"on","blur":None}


    pic_link = db.hget("{}:Level:Config".format(server_id),"pic")

    enable = db.get("{}:Level:pic".format(server_id))

    raw_data = [["Rank", "User", "Level", "EXP","Total EXP"]]
    for x in range(1,11):
        raw_data.append([str(x),"name","1","100","200"])

    img = Image.new("RGBA", (1000,1000), color=(0, 0, 0, 0))

    fnt = ImageFont.truetype('WhitneyBook.ttf', 12)
    fntb = ImageFont.truetype('WhitneySemiBold.ttf', 12)

    draw = ImageDraw.Draw(img)

    m = [0] * len(raw_data[0])
    for i, el in enumerate(raw_data):
        for j, e in enumerate(el):
            # if i == 0:
            #     wdth, hght = draw.textsize(e, font=fntb)
            #     if wdth > m[j]: m[j] = wdth
            # else:
            wdth, hght = draw.textsize(e, font=fnt)
            if wdth > m[j]: m[j] = wdth

    crop_width,crop_height = (10 + sum(m[:]) + 8 * len(m), 10 + 18 * len(raw_data) + 7)

    pic_data = db.hget("{}:Level:Config".format(server_id), "pic")

    if pic_data:
        r = requests.get(pic_data)
        if r.status_code == 200:
            pic = Image.open(io.BytesIO(r.content)) #read pic and save it to memory then declare new object called im (Image)
            aspectratio =  pic.width / pic.height
            pic = pic.resize((crop_width,int(crop_width / aspectratio)),Image.ANTIALIAS)
            pic = pic.crop(box = (0,int((pic.height-crop_height)/2),crop_width,int(crop_height+(pic.height-crop_height)/2)))
            if setting.get("blur") == "on":
                pic = pic.filter(ImageFilter.BLUR)
            img.paste(pic)
        else:
            flash("There is something wrong with this link, did they delete it?","warning")


    #adding text to picture
    """
    Runs enumerate twice as list is 2D
    It will take size of text and then return width and height
    then check if statement, for first run, which is first row (rank,user,level,exp,total exp)
    once i is not 0 anymore, It will run second statement which we can assume after first rows

    Those math are done to taken positions of putting text in

    draw.text(...)x4 for outlier then last one for overwrite and put white
    so it can be look like white text with black outlier
    """
    for i, el in enumerate(raw_data):
        for j, txt in enumerate(el):
            wdth, hght = draw.textsize(txt, font=fntb)
            font = fntb
            if i == 0:
                if j == 0:
                    w,h = (int(10 + (m[j] - wdth) / 2), 10)
                else:
                    w,h= (int(10 + sum(m[:j]) + (m[j] - wdth) / 2 + 8 * j), 10)
            else:
                if j == 0:
                    w,h = (int(10 + (m[j] - wdth) / 2), 10 + 18 * i + 5)
                else:
                    font = fnt
                    wdth, hght = draw.textsize(txt, font=fnt)
                    w,h= (int(10 + sum(m[:j]) + (m[j] - wdth) / 2 + 8 * j), 10 + 18 * i + 5)

            if setting.get("outlier") == "on": #outlier options
                draw.text((w - 1, h), txt, font=font,fill=outlier)
                draw.text((w + 1, h), txt, font=font,fill=outlier)
                draw.text((w, h - 1), txt, font=font,fill=outlier)
                draw.text((w, h + 1), txt, font=font,fill=outlier)

            draw.text((w, h), txt, font=font,fill=text) #main text
    del draw
    #making pic crop

    img = img.crop(box=(0, 0,crop_width,crop_height))


    draw = ImageDraw.Draw(img)

    if setting.get("border") == "on":
        #border area
        draw.line((5, 5, 5, img.size[1] - 5), fill=border, width=2)
        draw.line((5, 5, img.size[0] - 5, 5), fill=border, width=2)
        draw.line((5, img.size[1] - 5, img.size[0] - 4, img.size[1] - 5), fill=border, width=2)
        draw.line((img.size[0] - 5, 5, img.size[0] - 5, img.size[1] - 5), fill=border, width=2)
    if setting.get("row") == "on":
        #row/column lines
        for i in range(1, len(m)):
            draw.line((int(5 + sum(m[:i]) + 8 * i), 7, int(5 + sum(m[:i]) + 8 * i), img.size[1] - 5),fill=row, width=1)

        for i in range(1, len(raw_data)):
            if i == 1:
                draw.line((7, 7 + 18 * i + 2, img.size[0] - 5, 7 + 18 * i + 2), fill=row, width=2)
            else:
                draw.line((7, 7 + 18 * i + 7, img.size[0] - 5, 7 + 18 * i + 7), fill=row, width=1)
        del draw


    fp = io.BytesIO()
    img.save(fp, format='PNG')
    fp.seek(0)
    byes_pic = base64.b64encode(fp.read()).decode() #magic trick to make it like "str"....?

    return render_template("level/theme.html",pic = pic_link,pic_show = byes_pic,enable = enable, server=server,setting=setting,color=color_setting)

@blueprint.route('/update/theme/<int:server_id>', methods=['POST'])
@utils.plugin_method
def update_theme(server_id):
    enable = request.form.get("enable")
    pic = request.form.get("pic_link")

    #custom choices
    border = request.form.get("border")
    row = request.form.get("row")
    blur = request.form.get("blur")
    outlier = request.form.get("outlier")

    #color
    col_border = request.form.get("col_border")
    col_row = request.form.get("col_row")
    col_outlier = request.form.get("col_outlier")
    col_text = request.form.get("col_text")



    if pic != "":
        status = utils.check_link(pic)
    else:
        status = 0
    if status == 0:  # if is true
        db.hset("{}:Level:Config".format(server_id),"pic",pic)

        db.hset("{}:Level:pic_setting".format(server_id),"border",border)
        db.hset("{}:Level:pic_setting".format(server_id),"row",row)
        db.hset("{}:Level:pic_setting".format(server_id),"outlier",outlier)
        db.hset("{}:Level:pic_setting".format(server_id),"blur",blur)

        if not "" in (col_border,col_row,col_outlier,col_text):
            db.hset("{}:Level:color".format(server_id),"border",col_border)
            db.hset("{}:Level:color".format(server_id),"row",col_row)
            db.hset("{}:Level:color".format(server_id),"outlier",col_outlier)
            db.hset("{}:Level:color".format(server_id),"text",col_text)
        else:
            flash("You cannot have blank in color! Please click option above it for not having them","warning")
            return redirect(url_for("level.theme",server_id = server_id))
        if enable is None:
            db.delete("{}:Level:pic".format(server_id))
        else:
            db.set("{}:Level:pic".format(server_id),enable)
        flash("Successfully add!","success")

    return redirect(url_for("level.theme",server_id = server_id))

@blueprint.route('/css/<int:server_id>')
@utils.plugin_method
def css_theme(server_id):
    server = {
    'id':server_id,
    'name':db.hget("Info:Server",server_id),
    'icon':db.hget("Info:Server_Icon",server_id)}
    css = "Enter info here"
    try:
        with open("static/css/custom/{}.css".format(server_id),"r") as fp:
            css = fp.read()
    except FileNotFoundError:
        pass

    return render_template("css_page.html",server = server, css = css)

@blueprint.route('/update/css/<int:server_id>', methods=['POST'])
@utils.plugin_method
def update_css(server_id):
    with open("static/css/custom/{}.css".format(server_id),"w+") as fp:
        fp.write(request.form.get("css_info"))
        flash("Update","success")
    return redirect(url_for("level.css_theme",server_id = server_id))
