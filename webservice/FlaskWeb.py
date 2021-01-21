
# import new
import decimal
import boto3
from boto3.dynamodb.conditions import Key, Attr
from datetime import timedelta

import md5

import flask
from flask import Flask, render_template, session, request, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room, \
    close_room, rooms, disconnect

from flask import redirect
from flask_login import (LoginManager, login_required, login_user,
                         current_user, logout_user, UserMixin)


from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTShadowClient
import os, sys
import logging
import time
import getopt
import datetime as dt

import json

### Thread Package
import threading

from station import ChargingSite
from station import ChargingStation
from loggingcontroller import LogController
from station import SITES
from usermanage import User
from usermanage import TOKENTIMEOUTINTERVAL
import util

NAMESPACE = '/evsecontoller'
STATUSEVENT = 'sitestatus'
LOADEVENT = 'loadstatus'

# Custom Shadow callback
def customShadowdeltaCallback(payload):
    pass

async_mode = None
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode=async_mode)
thread = None

########### Web socket implementation Parts ##########
bSocketCommand = False
def enablesocket():
    global bSocketCommand
    bSocketCommand = True

def background_thread():
    while True:
        socketio.sleep(0.5)
        global bSocketCommand
        if(bSocketCommand == True):
            bSocketCommand = False
            payload = ChargingSite.generateSiteInfo()
            print(payload)
            print('socket message:' + payload)
            socketio.emit(LOADEVENT, {'data':payload}, namespace=NAMESPACE)

@socketio.on(LOADEVENT, namespace=NAMESPACE)
def loadstatus(message):
    payload = ChargingSite.generateSiteInfo()
    emit(LOADEVENT, {'data': payload})

@socketio.on('connect', namespace=NAMESPACE)
def socketcallback():
    payload = ChargingSite.generateSiteInfo()
    print(payload)
    global thread
    if thread is None:
        thread = socketio.start_background_task(target=background_thread)
    emit(LOADEVENT, {'data': payload})

@socketio.on('disconnect', namespace=NAMESPACE)
def disconnect():
    print('websocket client is disconnected, ', request.sid)

def stationdeltacallback(station):
    enablesocket()
    return

def stationupdatecallback(station):
    enablesocket()
    return

ChargingStation.deltashadowcallback = stationdeltacallback
ChargingStation.updateshadowcallback = stationupdatecallback

ChargingStation.example = 1

#Flask-Login Login Manager
login_manager = LoginManager()
@login_manager.user_loader
def load_user(user_id):
    print(user_id)
    user = User.get_fromid(user_id)
    return User.verify_auth_token(user.token)

'''
    pages for admin management
'''
@app.route('/')
def index_page():
    user_id = (current_user.get_id() or "No User Logged In")
    return render_template('dashboard.html', user_id=user_id)

@app.route('/maindash')
@login_required
def maindash():
    print('maindash is arrived')
    userlevel = User.get_fromid(current_user.get_id()).level
    print(userlevel)
    return render_template('maindash.html', username=current_user.get_id(), userlevel=str(userlevel))

@app.route('/getlogging')
@login_required
def geteventlist():
    print('event list')
    return LogController.getlogs()

@app.route('/sitemanger')
@login_required
def sitemanger():
    userlevel = User.get_fromid(current_user.get_id()).level
    return render_template('sitemanger.html', username=current_user.get_id(), userlevel=str(userlevel))

@app.route('/evenlogview')
@login_required
def evenlogview():
    userlevel = User.get_fromid(current_user.get_id()).level
    return render_template('evenlogview.html', username=current_user.get_id(), userlevel=str(userlevel))

@app.route('/usermanager')
@login_required
def usermanager():
    userlevel = User.get_fromid(current_user.get_id()).level
    return render_template('usermanager.html', username=current_user.get_id(), userlevel=str(userlevel))

@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if request.method == 'POST':
        user = User.get(request.form['usermail'])
        if user and User.hash_pass(request.form['password']) == user.password:
            login_user(user, remember=True)

            ### user login timeout interval
            user.generate_auth_token(TOKENTIMEOUTINTERVAL)

            # send response
            userdata = dict()
            userdata['user_id'] = user.id
            userdata['email'] = user.email
            userdata['level'] = user.level
            return jsonify(userdata)

        else:
            return jsonify(None)
    return render_template("login.html")

### When no free page, we have to use these code
'''
    if(current_user.is_authenticated):
        return render_template('dashboard.html', user_id=user_id)
    else:
        global bThread
        bThread = True
        return render_template('login.html')
'''

@app.route('/logout')
@login_required
def logout_page():
    logout_user()
    return redirect("/")


'''
    definitions of API 
'''
@app.route('/getuser')
@login_required
def getuser():
    return User.getuserlist()

@app.route('/adduser', methods=['GET', 'POST'])
@login_required
def adduser():
    ret_data = dict()
    try:
        if request.method == 'POST':
            userlevel = User.get_fromid(current_user.get_id()).level

            if(int(userlevel) == int(User.ADMINLEVEL)):

                userid = request.form['userid']
                email = request.form['email']
                password = request.form['password']
                level = request.form['level']

                if(User.newuser(userid, email, password, int(level))):
                    ret_data['result'] = True

                    ### Add event logging
                    message = 'added new user, userid-' + userid + ', email-' + email
                    LogController.addEventLogging(userid=current_user.get_id(), detail=message)

                else:
                    ret_data['result'] = False
                    ret_data['reason'] = 'error happened in adding user to dynamodb'
            else:
                ret_data['result'] = False
                ret_data['reason'] = 'user level is restricetd'
    except:
        pass
    return jsonify(ret_data)

@app.route('/deluser', methods=['GET', 'POST'])
@login_required
def deluser():
    ret_data = dict()
    try:
        if request.method == 'POST':
            userlevel = User.get_fromid(current_user.get_id()).level
            if(int(userlevel) == int(User.ADMINLEVEL)):
                userid = request.form['userid']
                email = request.form['email']

                if(User.deluser(userid, email)):
                    ret_data['result'] = True

                    ### add event log
                    message = 'deleted user, userid-' + userid + ', email-' + email
                    LogController.addEventLogging(userid=current_user.get_id(), detail=message)

                else:
                    ret_data['result'] = False
                    ret_data['reason'] = 'error in deleting user'
            else:
                ret_data['result'] = False
                ret_data['reason'] = 'user level is restricetd'
    except:
        pass

    return jsonify(ret_data)

@app.route('/getsite')
@login_required
def getsitelist():
    ret_data = []
    for site in SITES:
        ret_data.append(site.sitename)
    return jsonify(ret_data)

@app.route('/addstation', methods=['GET', 'POST'])
@login_required
def addstation():
    ret_data = dict()
    if request.method == 'POST':
        userlevel = User.get_fromid(current_user.get_id()).level
        if(int(userlevel) == int(User.ADMINLEVEL)):
            sitename = request.form['sitename']
            stationName = request.form['shadowName']

            site = ChargingSite.get_site(sitename)
            if(site == None):
                ret_data['result'] = False
                ret_data['reason'] = 'sitename is invalid'
                print(json.dumps(ret_data))
            else:
                if(site.add_station(stationName) == True):
                    ret_data['result'] = True
                    message = 'added station ' + stationName + ' in site ' + sitename
                    LogController.addEventLogging(userid=current_user.get_id(), detail=message)
                else:
                    ret_data['result'] = False
                    ret_data['reason'] = 'station is invalid or database error'
        else:
            ret_data['result'] = False
            ret_data['reason'] = 'user level is restricetd'
    else:
        ret_data['result'] = False
    return jsonify(ret_data)

@app.route('/delstation', methods=['GET', 'POST'])
@login_required
def delstation():
    ret_data = dict()
    if request.method == "POST":
        userlevel = User.get_fromid(current_user.get_id()).level
        if(int(userlevel) == int(User.ADMINLEVEL)):
            sitename = request.form['sitename']
            stationName = request.form['shadowName']
            site = ChargingSite.get_site(sitename)
            if(site == None):
                ret_data['result'] = False
                ret_data['reason'] = 'sitename is invalid'
                print(json.dumps(ret_data))
            else:
                if(site.del_station(stationName) == True):
                    ret_data['result'] = True

                    message = 'delete station ' + stationName
                    message += ' in ' + sitename
                    LogController.addEventLogging(userid=current_user.get_id(), detail=message)
                else:
                    ret_data['result'] = False
                    ret_data['reason'] = 'station is invalid or database error'
        else:
            ret_data['result'] = False
            ret_data['reason'] = 'user level is restricetd'
    else:
        ret_data['result'] = False
    return jsonify(ret_data)

@app.route('/updatestation', methods=['GET', 'POST'])
@login_required
def updatestation():
    ret_data = dict()
    try:
        if request.method == 'POST':
            userlevel = User.get_fromid(current_user.get_id()).level
            if(int(userlevel) == int(User.ADMINLEVEL)):

                sitename = request.form['sitename']
                shadowName = request.form['shadowName']

                site = ChargingSite.get_site(sitename)

                if(site == None):
                    ret_data['result'] = False
                    ret_data['reason'] = 'sitename is invalid'
                else:
                    message = ''
                    message += 'update station information, site:'
                    message += sitename

                    message += ', station:'
                    message += shadowName

                    if ('serialNumber' in request.form):
                        serialNumber = request.form['serialNumber']
                        message += ', SerialNumber:'
                        message += serialNumber
                    else:
                        serialNumber = None

                    if ('charge_max' in request.form):
                        charge_max = int(request.form['charge_max'])
                        message += ', charge_max:'
                        message += str(charge_max)
                    else:
                        charge_max = None

                    if ('activate' in request.form):
                        activate = util.str_to_bool(request.form['activate'])
                        message += ', activate:'
                        message += request.form['activate']
                    else:
                        activate = None

                    if ('present_power' in request.form):
                        present_power = int(request.form['present_power'])
                        message += ', present_power:'
                        message += str(present_power)
                    else:
                        present_power = None

                    if(site.update_station(shadowName, serialNumber, charge_max, present_power, activate)):
                        ret_data['result'] = True
                        LogController.addEventLogging(userid=current_user.get_id(), detail=message)
                    else:
                        ret_data['result'] = False
                        ret_data['reason'] = 'station is invalid or database error'
            else:
                ret_data['result'] = False
                ret_data['reason'] = 'user level is restricetd'
        else:
            ret_data['result'] = False
    except:
        print('error')

    print(json.dumps(ret_data))
    return jsonify(ret_data)

@app.route('/updatesite', methods=['GET', 'POST'])
@login_required
def updatesite():
    ret_data = dict()
    if request.method == 'POST':
        userlevel = User.get_fromid(current_user.get_id()).level
        if(int(userlevel) == int(User.ADMINLEVEL)):

            sitename = request.form['sitename']
            site = ChargingSite.get_site(sitename)

            if(site != None):
                message = ''
                message += 'update site information, site:'
                message += sitename

                if ('serialnumber' in request.form):
                    serialnumber = request.form['serialnumber']
                    message += ', SerialNumber from '
                    message += site.serialNumber
                    message += ' to '
                    message += serialnumber
                else:
                    serialnumber = None

                if ('longitude' in request.form):
                    longitude = request.form['longitude']

                    message += ', longitude from '
                    message += site.longitude
                    message += ' to '
                    message += longitude
                else:
                    longitude = None

                if ('latitude' in request.form):
                    latitude = request.form['latitude']

                    message += ', latitude from '
                    message += site.latitude
                    message += ' to '
                    message += latitude

                else:
                    latitude = None

                if ('supply' in request.form):
                    supply = request.form['supply']
                    message += ', supply from '
                    message += str(site.supply)
                    message += ' to '
                    message += supply
                else:
                    supply = None

                if(ChargingSite.update_site(sitename, serialnumber, longitude, latitude, supply)):
                    ret_data['result'] = True

                    LogController.addEventLogging(userid=current_user.get_id(), detail=message)

                    ### enable socket emit to all client
                    enablesocket()

                else:
                    ret_data['result'] = False
                    ret_data['reason'] = 'Failed to update'
            else:
                ret_data['result'] = False
                ret_data['reason'] = 'sitename does not exist'
        else:
            ret_data['result'] = False
            ret_data['reason'] = 'user level is restricetd'
    else:
        ret_data['result'] = False
    return jsonify(ret_data)

@app.route('/addsite', methods=['GET', 'POST'])
@login_required
def addsite():
    ret_data = dict()
    #if request.method == "GET":
    if request.method == "POST":
        userlevel = User.get_fromid(current_user.get_id()).level
        if(int(userlevel) == int(User.ADMINLEVEL)):

            sitename = request.form['sitename']
            longitude = request.form['longitude']
            latitude = request.form['latitude']

            if(ChargingSite.add_site(sitename, longitude, latitude) == True):
                ret_data['result'] = True
                message = 'new site operation: site name is ' + sitename
                LogController.addEventLogging(userid=current_user.get_id(), detail=message)
            else:
                ret_data['result'] = False
                ret_data['reason'] = 'adding new site is failed'
        else:
            ret_data['result'] = False
            ret_data['reason'] = 'user level is restricetd'
    else:
        ret_data['result'] = False
    return jsonify(ret_data)

@app.route('/delsite', methods=['GET', 'POST'])
@login_required
def delsite():
    ret_data = dict()
    if request.method == "POST":
        userlevel = User.get_fromid(current_user.get_id()).level
        if(int(userlevel) == int(User.ADMINLEVEL)):
            sitename = request.form['sitename']
            if(ChargingSite.del_site(sitename) == True):
                ret_data['result'] = True
                message = 'delete site: site name is ' + sitename
                LogController.addEventLogging(userid=current_user.get_id(), detail=message)
            else:
                ret_data['result'] = False
                ret_data['reason'] = 'delete site is failed'
        else:
            ret_data['result'] = False
            ret_data['reason'] = 'user level is restricetd'
    else:
        ret_data['result'] = False
    return jsonify(ret_data)

@app.route('/restricted')
def restricted_page():
    user_id = (current_user.get_id() or 'No User Logged In')
    return render_template('restricted.html', user_id=user_id)

if __name__ == '__main__':
    try:
        ChargingSite.load_Siteinfo()
        User.getUserDataFromDynamoDB()
        app.config["REMEMBER_COOKIE_DURATION"] = timedelta(hours=1)

        #Tell the login manager where to redirect users to display the login page
        login_manager.login_view = '/login/'

        #Setup the login manager.
        login_manager.setup_app(app)
        socketio.run(app, debug=False, host='0.0.0.0', port=80)
    except KeyboardInterrupt:
        print('program ended')