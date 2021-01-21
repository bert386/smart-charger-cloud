
#import new
import decimal
import boto3
from boto3.dynamodb.conditions import Key, Attr
from datetime import timedelta

import md5

from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTShadowClient
import os, sys
import logging
import time
import json
import getopt
import datetime as dt

### Thread Package
import threading
import urllib2

import util
from loggingcontroller import LogController

'''
    Constants 
'''
EVSE_STATE_UNKNOWN 			= 0x00
EVSE_STATE_A 				= 0x01 # vehicle state A 12V - not connected
EVSE_STATE_B 				= 0x02 # vehicle state B 9V - connected, ready
EVSE_STATE_C 				= 0x03 # vehicle state C 6V - charging
EVSE_STATE_D 				= 0x04 # vehicle state D 3V - vent required
EVSE_STATE_DIODE_CHK_FAILED = 0x05 # diode check failed
EVSE_STATE_GFCI_FAULT 		= 0x06 # GFCI fault
EVSE_STATE_NO_GROUND 		= 0x07 # bad ground
EVSE_STATE_STUCK_RELAY 		= 0x08 # stuck relay
EVSE_STATE_GFI_TEST_FAILED	= 0x09 # GFI self-test failure
EVSE_STATE_OVER_TEMPERATURE = 0x0A # over temperature error shutdown

EVSE_STATE_SLEEPING 		= 0xFE # waiting for timer
EVSE_STATE_DISABLED 		= 0xFF # disabled

THINGTYPE = 'Evse_Gateway'

#### Configuration variables, in the future , we will implement configuration file
host = 'a225oj6drt7gf8.iot.us-east-1.amazonaws.com'
rootCAPath = 'root-CA.crt'
certificatePath = 'evseweb.cert.pem'
privateKeyPath = 'evseweb.private.key'

'''
# Configure logging
logger = logging.getLogger("AWSIoTPythonSDK.core")
logger.setLevel(logging.DEBUG)
streamHandler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
streamHandler.setFormatter(formatter)
logger.addHandler(streamHandler)
'''

# Init AWSIoTMQTTShadowClient
myAWSIoTMQTTShadowClient = None
myAWSIoTMQTTShadowClient = AWSIoTMQTTShadowClient("OpenEvse_backend")
myAWSIoTMQTTShadowClient.configureEndpoint(host, 8883)
myAWSIoTMQTTShadowClient.configureCredentials(rootCAPath, privateKeyPath, certificatePath)

# AWSIoTMQTTShadowClient configuration
myAWSIoTMQTTShadowClient.configureAutoReconnectBackoffTime(1, 32, 20)
myAWSIoTMQTTShadowClient.configureConnectDisconnectTimeout(10)  # 10 sec
myAWSIoTMQTTShadowClient.configureMQTTOperationTimeout(5)  # 5 sec
myAWSIoTMQTTShadowClient.connect()

SITES = []

def deleteTopicRule(shadowname):
    try:
        client = boto3.client('iot')
        response = client.delete_topic_rule(
            ruleName='rule_' + shadowname
        )
    except:
        print('delete topicrule error!')

def createTopicRule(shadowname):
    try:
        client = boto3.client('iot')
        response = client.create_topic_rule(
            ruleName='rule_' + shadowname,
            topicRulePayload={
                'sql': 'SELECT * FROM "my/things/' + shadowname + '/update"',
                'description': 'republish rule for ' + shadowname,
                'actions': [
                    {
                        'republish': {
                            'roleArn': 'arn:aws:iam::546371203800:role/service-role/aws_iot_republish',
                            'topic': '$$aws/things/' + shadowname + '/shadow/update'
                        },
                    },
                ],
                'ruleDisabled': False
            }
        )
    except:
        print('createtopic rule error!')

class ChargingSite():

    def __init__(self, sitename, serialNumber, latitude, longitude):
        self.sitename = sitename
        self.serialNumber = serialNumber
        self.latitude = latitude
        self.longitude = longitude
        self.supply = 0
        self.stations = []


    def add_station(self, shadowName):
        for site in SITES:
            for station in site.stations:
                if (station.shadowName == shadowName):
                    print('shadow instance of same name is already exist')
                    return False

        serialNumber = 'STATION_' + util.randomint(10)
        try:
            # create iot thing
            client = boto3.client('iot')
            response = client.create_thing(
                thingName=shadowName,
                thingTypeName=THINGTYPE,
            )

        except:
            print('error happens in iot create thing')
            return False

        createTopicRule(shadowName)

        try:
            station = ChargingStation(myAWSIoTMQTTShadowClient, shadowName, serialNumber, None)
            while(station.shadowworking):
                pass

            self.stations.append(station)
            print(len(self.stations))
            ChargingSite.update_site(sitename=self.sitename)

        except:
            print('error happens in update site')
            pass

        return True

    def get_station(self, shadowName):
        for station in self.stations:
            if (station.shadowName == shadowName):
                return station

        return None

    def update_station(self, shadowName, serialNumber=None, charge_max=None, present_power=None, activate=None):
        station = self.get_station(shadowName)
        if(station == None):
            print('Invalid station name ')
            return False

        if(serialNumber != None):
            station.setSerialNumber(serialNumber)
            return True

        ### Only when device is connected to network
        if(station.iotConnected):
            return False

        if(charge_max != None):
            station.setCharge_max(charge_max)

        if(present_power != None):
            station.setPresent(present_power)

        if(activate != None):
            if(activate == True):
                station.active()
            else:
                station.deactive()

        # ChargingSite.update_site(sitename=self.sitename)
        return True

    def del_station(self, shadowName):
        for station in self.stations:
            if (station.shadowName == shadowName):
                try:
                    client = boto3.client('iot')
                    response = client.delete_thing(
                        thingName=shadowName
                    )
                except:
                    print('error happens in iot delete thing')
                    return False

                try:
                    deleteTopicRule(shadowName)
                except:
                    return False

                try:
                    self.stations.remove(station)
                    print(len(self.stations))
                    ChargingSite.update_site(sitename=self.sitename)

                except:
                    print('error happens in delete station')
                    return False
                return True

        print('There is no target station in this charging site')
        return False

    @staticmethod
    def load_Siteinfo():
        try:
            dynamodb = boto3.client('dynamodb')
            response = dynamodb.scan(
                ProjectionExpression='sitename, serialNumber, latitude, longitude, stations, supply',
                TableName='Sites',
            )

            for siteinfo in response['Items']:
                sitename = siteinfo['sitename']['S']
                serialNumber = siteinfo['serialNumber']['S']
                latitude = siteinfo['latitude']['S']
                longitude = siteinfo['longitude']['S']
                site = ChargingSite(sitename, serialNumber, latitude, longitude)
                if ('supply' in siteinfo):
                    site.supply = int(siteinfo['supply']['N'])

                if ('stations' in siteinfo):
                    stationsString = siteinfo['stations']['S']
                    shadowlist = json.loads(stationsString)
                    for shadowName in shadowlist:
                        print('Shadow Name is ' + shadowName)
                        station = ChargingStation(myAWSIoTMQTTShadowClient, shadowName, '', None)
                        site.stations.append(station)
                SITES.append(site)
        except:
            print('load error')
            pass

    @staticmethod
    def generateSiteInfo():
        sites = []
        for site in SITES:
            siteinfo = dict()

            siteinfo['sitename'] = site.sitename
            siteinfo['serialNumber'] = site.serialNumber
            siteinfo['latitude'] = float(site.latitude)
            siteinfo['longitude'] = float(site.longitude)
            siteinfo['supply'] = site.supply

            stations = []

            for station in site.stations:
                stationinfo = dict()
                stationinfo['shadowName'] = station.shadowName
                stationinfo['serialNumber'] = station.serialNumber
                stationinfo['iotConnected'] = station.iotConnected
                stationinfo['activate'] = station.activate
                stationinfo['present_power'] = station.present_power
                stationinfo['charge_curr'] = station.charge_curr
                stationinfo['charge_volt'] = station.charge_volt
                stationinfo['charge_max'] = station.charge_max
                stationinfo['charge_min'] = station.charge_min
                stationinfo['station_state'] = station.station_state
                stations.append(stationinfo)

            siteinfo['stations'] = stations
            sites.append(siteinfo)
        return json.dumps(sites)

    @staticmethod
    def del_site(sitename):
        print('delete site method')
        site = ChargingSite.get_site(sitename)
        if (site == None):
            print('Not found destination ')
            return False
        try:

            for station in site.stations:
                try:
                    client = boto3.client('iot')
                    response = client.delete_thing(
                        thingName=station.shadowName
                    )
                except:
                    print('error happens in iot delete thing')

                try:
                    deleteTopicRule(station.shadowName)
                except:
                    pass

            SITES.remove(site)
            dynamodb = boto3.client('dynamodb')
            response = dynamodb.delete_item(Key={'sitename': {'S': sitename, }}, TableName='Sites')

        except:
            print('delete item error in DynamoDB')
            return False
        return True

    @staticmethod
    def add_site(sitename, latitude, longitude):
        print('addsite method')
        if(ChargingSite.get_site(sitename) != None):
            return False
        serialNumber = 'ES_' + util.randomint(12)
        print('serial number is ' + serialNumber)
        try:
            SITES.append(ChargingSite(sitename, serialNumber, latitude, longitude))
            dynamodb = boto3.client('dynamodb')

            response = dynamodb.put_item(
                Item={
                    'sitename': {
                        'S': sitename,
                    },
                    'serialNumber': {
                        'S': serialNumber,
                    },
                    'latitude': {
                        'S': str(latitude),
                    },
                    'longitude': {
                        'S': str(longitude),
                    },
                },
                ReturnConsumedCapacity='TOTAL',
                TableName='Sites',
            )
        except:
            print('put item error in DynamoDB')
            return False
        return True

    @staticmethod
    def get_site(sitename):
        # get site instance
        try:
            for site in SITES:
                if (site.sitename == sitename):
                    return site
        except:
            print('unknown error')
        return None

    '''
    '''
    @staticmethod
    def update_site(sitename, serialNumber=None, latitude=None, longitude=None, supply=None):
        site = ChargingSite.get_site(sitename)

        if(site == None):
            print('Not found site with specified name')
            return False
        try:
            if(serialNumber != None):
                site.serialNumber = serialNumber

            if(latitude != None):
                site.latitude = latitude

            if(longitude != None):
                site.longitude = longitude

            if(supply != None):
                if(isinstance(int(supply), int)):
                    print('supply is ' + supply)
                    site.supply = int(supply)

            stationlist = []
            for station in site.stations:
                stationlist.append(station.shadowName)

            dynamodb = boto3.client('dynamodb')
            response = dynamodb.put_item(
                Item={
                    'sitename': {
                        'S': site.sitename,
                    },
                    'serialNumber': {
                        'S': site.serialNumber,
                    },
                    'latitude': {
                        'S': str(site.latitude),
                    },
                    'longitude': {
                        'S': str(site.longitude),
                    },
                    'supply': {
                        'N': str(site.supply),
                    },
                    'stations': {
                        'S' : json.dumps(stationlist),
                    },
                },
                ReturnConsumedCapacity='TOTAL',
                TableName='Sites',
            )
        except:
            print('update item error in DynamoDB')
            return False
        return True


class ChargingStation():

    deltashadowcallback = None
    updateshadowcallback = None

    def __init__(self, myAWSIoTMQTTShadowClient, shadowName, serialNumber='', customShadowdeltaCallback=None):

        self.shadowName = shadowName
        self.serialNumber = '' # changed user side
        self.iotConnected = False # controlled by bundle, only reported ()
        self.activate = False # controller by user and backend
        self.present_power = 0 #
        self.charge_max = 0 # reported

        self.charge_min = 0 # reported
        self.charge_curr = 0 # reported
        self.charge_volt = 0 # reported
        self.station_state = 0 # reported

        self.deviceShadowInstance = myAWSIoTMQTTShadowClient.createShadowHandlerWithName(shadowName, True)
        self.deviceShadowInstance.shadowRegisterDeltaCallback(self.deltaCallback)

        if(serialNumber != ''):
            self.serialNumber = serialNumber
            newPayload = '{"state":{"reported":{"serialNumber": "' + serialNumber + '"}}}'
            self.shadowworking = True
            self.deviceShadowInstance.shadowUpdate(newPayload, self.updateCallback, 3)
            while(self.shadowworking):
                pass

        self.shadowworking = True
        self.deviceShadowInstance.shadowGet(self.getCallback, 5)
        while(self.shadowworking):
            pass

    def echostate(self, payload):
        newPayload = '{"state":{"reported":' + payload + '}}'
        self.deviceShadowInstance.shadowUpdate(newPayload, None, 5)

    def active(self):
        newPayload = '{"state":{"desired":{"activate": true}}}'
        print('update ' + newPayload)
        self.deviceShadowInstance.shadowUpdate(newPayload, self.updateCallback, 3)

    def deactive(self):
        newPayload = '{"state":{"desired":{"activate": false}}}'
        print('update ' + newPayload)
        self.deviceShadowInstance.shadowUpdate(newPayload, self.updateCallback, 3)

    def setPresent(self, present_power):
        print('present power setting ' + str(present_power))
        self.present_power = present_power
        newPayload = '{"state":{"desired":{"present_power":' + str(present_power) + '}}}'
        self.deviceShadowInstance.shadowUpdate(newPayload, self.updateCallback, 3)

    def setSerialNumber(self, serialNumber):
        self.serialNumber = serialNumber
        newPayload = '{"state":{"desired":{"serialNumber":' + str(serialNumber) + '}}}'
        self.deviceShadowInstance.shadowUpdate(newPayload, self.updateCallback, 3)

    def setCharge_max(self, charge_max):
        print('charge max setting ' + str(charge_max))
        self.charge_max = charge_max
        newPayload = '{"state":{"desired":{"charge_max":' + str(charge_max) + '}}}'
        self.deviceShadowInstance.shadowUpdate(newPayload, self.updateCallback, 3)

    def getCallback(self, payload, responseStatus, token):
        if(responseStatus == 'accepted'):
            payloadDict = json.loads(payload)

            payloadDict = payloadDict['state']
            print(payloadDict)

            if(u'reported' in payloadDict):
                reportedDict = payloadDict[u'reported']

                if(u'serialNumber' in reportedDict):
                    self.serialNumber = reportedDict[u'serialNumber']

                if(u'iotConnected' in reportedDict):
                    self.iotConnected = reportedDict[u'iotconnected']

                if(u'activate' in reportedDict):
                    self.activate = reportedDict[u'activate']

                if(u'present_power' in reportedDict):
                    self.present_power = reportedDict[u'present_power']

                if(u'charge_max' in reportedDict):
                    self.charge_max = reportedDict[u'charge_max']

                if(u'station_state' in reportedDict):
                    self.station_state = reportedDict[u'station_state']

                if(u'charge_curr' in reportedDict):
                    self.charge_curr = reportedDict[u'charge_curr']

                if(u'charge_volt' in reportedDict):
                    self.charge_volt = reportedDict[u'charge_volt']

                if(u'charge_min' in reportedDict):
                    self.charge_min = reportedDict[u'charge_min']


            if(u'delta' in payloadDict):
                reported = dict()
                deltaDict = payloadDict[u'delta']

                toreport = False

                if(u'charge_min' in deltaDict):
                    self.charge_min = deltaDict[u'charge_min']
                    reported['charge_min'] = deltaDict[u'charge_min']
                    toreport = True

                if(u'charge_curr' in deltaDict):
                    self.charge_curr = deltaDict[u'charge_curr']
                    reported['charge_curr'] = deltaDict[u'charge_curr']
                    toreport = True

                if(u'charge_volt' in deltaDict):
                    self.charge_volt = deltaDict[u'charge_volt']
                    reported['charge_volt'] = deltaDict[u'charge_volt']
                    toreport = True

                if(u'station_state' in deltaDict):
                    self.station_state = deltaDict[u'station_state']
                    reported['station_state'] = deltaDict[u'station_state']
                    toreport = True

                if(toreport):
                    newPayload = '{"state":{"reported":' + json.dumps(reported) + '}}'
                    self.deviceShadowInstance.shadowUpdate(newPayload, None, 3)
        self.shadowworking = False

    def updateCallback(self, payload, responseStatus, token):
        if(responseStatus == "timeout"):
            print("Update request " + token + " time out!")

        if(responseStatus == "accepted"):
            payloadDict = json.loads(payload)
            payloadDict = payloadDict['state']
            print('update accepted')
            print(payload)

            if('desired' in payloadDict):
                payloadDict = payloadDict['desired']

                if('activate' in payloadDict):
                    self.activate = payloadDict['activate']

                if(u'present_power' in payloadDict):
                    self.present_power = payloadDict[u'present_power']

                if(u'charge_max' in payloadDict):
                    self.present_power = payloadDict[u'charge_max']

            if(ChargingStation.updateshadowcallback != None):
                ChargingStation.updateshadowcallback(self)

        if(responseStatus == "rejected"):
            print("Update request " + token + " rejected!")

        self.shadowworking = False

    def deltaCallback(self, payload, responseStatus, token):
        print("Received a delta message:")
        payloadDict = json.loads(payload)
        deltaMessage = json.dumps(payloadDict["state"])
        print(deltaMessage)

        commandDict = json.loads(deltaMessage)
        commandDict['shadowName'] = self.shadowName
        echo = False

        if ('iotConnected' in commandDict):
            self.iotConnected = commandDict['iotConnected']
            logmsg = ''
            if(self.iotConnected == True):
                logmsg = 'charging station ' + self.shadowName + ' is connected to AWS IOT.'
            else:
                logmsg = 'charging station ' + self.shadowName + ' is disconnected to AWS IOT.'
            LogController.addEventLogging(detail=logmsg)
            echo = True

        if ('station_state' in commandDict):
            self.station_state = commandDict['station_state']
            logmsg = 'charging station ' + self.shadowName + ' state changed to '
            if(self.station_state == EVSE_STATE_A):
                logmsg += 'EV disconnected status'
            elif(self.station_state == EVSE_STATE_B):
                logmsg += 'EV connecetd(charging ready) status'
            elif(self.station_state == EVSE_STATE_C):
                logmsg += 'charging status'
            elif(self.station_state == EVSE_STATE_D):
                logmsg += 'charging completed'

            LogController.addEventLogging(detail=logmsg)
            echo = True

        #if ('charge_max' in commandDict):
        #    self.charge_max = commandDict['charge_max']
        #    echo = True

        if ('charge_min' in commandDict):
            self.charge_min = commandDict['charge_min']
            echo = True

        if ('charge_curr' in commandDict):
            self.charge_curr = commandDict['charge_curr']
            echo = True

        if ('charge_volt' in commandDict):
            self.charge_volt = commandDict['charge_volt']
            echo = True

        if (echo == True):
            print("Request to update the reported state...")
            newPayload = '{"state":{"reported":' + payload + '}}'
            self.deviceShadowInstance.shadowUpdate(newPayload, None, 5)
            print("Sent.")
            if(ChargingStation.deltashadowcallback != None):
                ChargingStation.deltashadowcallback(self)
