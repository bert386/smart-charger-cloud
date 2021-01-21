'''
	OpenEvse Controller IOT Gateway

	Author		Jinzhouyun
	Last daate	201707
	email		2435575291@qq.com
	Version 	1.5
 '''
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTShadowClient
import os, sys
import logging
import time
import json
import getopt
import datetime as dt

### Thread Package
import threading

# this is for UART for Raspberry Pi
import serial
import urllib2

import utils
import Queue

#### Configuration variables, in the future , we will implement configuration file
host = "a225oj6drt7gf8.iot.us-east-2.amazonaws.com"
rootCAPath = "root-CA.crt"
certificatePath = "OpenEvse001.cert.pem"
privateKeyPath = "OpenEvse001.private.key"
#### IOT device Shadow Name
shadowName = 'OpenEvse001'

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

ENABLE_COMMAND = ''

'''
	UART instance for USB Serial, 
	
'''
#serialport = serial.Serial("/dev/ttyUSB0", 9600, timeout=0.5) # Baudrate 9600, Timeout 0.5sec
serialport = serial.Serial("/dev/ttyS0", 9600, timeout=1) # Baudrate 9600, Timeout 0.5sec

### Request Queue
reqQueue = Queue.Queue()


#### Uart Buffer Count ####
RAPIMAXLEN = 30


######################## Thread for read Packet from controller using RAPI Protocol
class RAPIProc(threading.Thread):
	def __init__(self):
		threading.Thread.__init__(self)

		# Threading Event instance
		self.currEvent = threading.Event()

		# last communication time variable
		self.lasttime = dt.datetime.now()

		# resposne buffer from Evse Controller via UART
		self.response = ['0'] * RAPIMAXLEN

		# Get Status Request interval(millisec uint)
		self.queueInterval = 15000
		self.requestInterval = 1000

		#
		self.lastQueueTime = 0
		self.lastReqTime = 0
		self.lastRespTime = 0

	def run(self):

		global reqQueue
		global serialport

		global evesGate

		while not self.currEvent.isSet():
			# get async response relevant to status
			resp = serialport.readline().decode()
			if(len(resp) > 0):
				print('state async message from controller - ' + resp)
				type = resp[1:3]
				statecode = int(resp[4:6])
				newPayload = '{"state":{"desired":{"station_state":' + str(statecode) + '}}}'
				evesGate.deviceShadowInstance.shadowUpdate(newPayload, None, 5)
				print('update message ' + newPayload)

			if (utils.millis() - self.lastQueueTime >= self.requestInterval):
				### Add requests into queue
				reqQueue.put('$GS*BE\r') # Get state
				reqQueue.put('$GG*B2\r') # get charging current and voltage
				reqQueue.put('$GC*AE\r') # get charging capacity
				self.lastQueueTime = utils.millis()

			if(not reqQueue.Empty()):
				command = reqQueue.get()
				buff = command.encode()

				# Write Request Packet
				serialport.write(buff)
				resp = serialport.readline().decode()

				if(len(resp) > 0):
					evesGate.timeout(False)
					# check command type
					type = command[1:4]
					if(type == 'GS'):
						# Get state
						currstate = int(resp[4:5])
						evesGate.updateState(currstate)

					elif(type == 'GG'):
						# get charging current & voltage
						firstspace = resp.find(' ')
						secondspace = resp.find(' ', firstspace + 1)
						if(firstspace != -1 and secondspace != -1):
							current = int(resp[firstspace + 1:secondspace])
							voltage = int(resp[secondspace + 1:])
							evesGate.updateCurVolt(current, voltage)

					elif(type == 'GC'):
						# get charging capacity
						firstspace = resp.find(' ')
						secondspace = resp.find(' ', firstspace + 1)
						if(firstspace != -1 and secondspace != -1):
							max = int(resp[firstspace + 1:secondspace])
							min = int(resp[secondspace + 1:])
							evesGate.updateChargingCapacity(max, min)

				else:
					evesGate.timeout(True)


				self.lastReqTime = utils.millis()

				'''
				buff = reqQueue.get().encode()
				serialport.write(buff)
				self.lastReqTime = utils.millis()
				'''

			resp = serialport.readline()
			length = len(resp)
			if(length > 0): # Reponse Process
				print 'Response from controller is received!'
				self.response(resp)
				# we can add process code in it

	################## #####################
	def response(self, response): # Process part for response
		return True

'''
	OpenEvse Controller Abstract class, 
	We have to define and implement action and functionalities for OpenEvse GateWay in this class.
	This is main class in Gateway.
	Gateway history 
		- 2017.07.22
		- 2017.07.16
		- 2017.06.27
		- 2017.06.17
			Mqtt Last will message to notice for AWS IOT whether device is connecetd and disconnected.
		- 2017.06.10 : 
			Only Enable and Disable Commands
'''
class OpenEvseGateWay():

	def __init__(self, deviceShadowInstance):
		self.deviceShadowInstance = deviceShadowInstance
		self.rapiProc = RAPIProc()
		self.rapiProc.start()
		self.timeoutflag = False

	def updateChargingCapacity(self, maximum, minimum):
		print('maximum charging current will be updated in deviceshadow')
		newPayload = '{"state": {"desired": {"charge_max":' + str(maximum) + ', "charge_min":' + str(minimum) + '}}}'
		self.deviceShadowInstance.shadowUpdate(newPayload, None, 5)

	def updateCurVolt(self, current, voltage):
		print('charging current will be updated in deviceshadow')
		newPayload = '{"state": {"desired": {"charge_curr":' + str(current / 1000.0) + ', "charge_volt":' + str(voltage / 1000.0) + '}}}'
		self.deviceShadowInstance.shadowUpdate(newPayload, None, 5)

	def updateState(self, newState):
		print('station state will be changed in deviceshadow')
		newPayload = '{"state": {"desired": {"station_state":' + str(newState) + '}}}'
		self.deviceShadowInstance.shadowUpdate(newPayload, None, 5)

	# enable action for Evse controller
	def activate(self):
		global reqQueue
		reqQueue.put('$FE*AF\r')

	# disable action for Evse controller
	def deactivate(self):
		global reqQueue
		reqQueue.put('$FD*AE\r')

	def timeout(self, timeout):
		if(timeout == True):
			if(self.timeoutflag == False):
				self.timeoutflag = True
				deviceshadow.shadowUpdate('{"state":{"desired":{"timeout":true}}}', None, 5)
		else:
			if (self.timeoutflag == True):
				self.timeoutflag = False
				deviceshadow.shadowUpdate('{"state":{"desired":{"timeout":false}}}', None, 5)

	def ShadowCallback_Delta(self, payload, responseStatus, token):
		print("Received a delta message:")
		payloadDict = json.loads(payload)
		deltaMessage = json.dumps(payloadDict["state"])
		print(deltaMessage)

		commandDict = json.loads(deltaMessage)
		if('activate' in commandDict):
			response = commandDict['activate'] and 'enable' or 'disable'
			print('accepted activate command is ' + response)
			if(commandDict['activate']):
				self.activate()
				print 'Enable command is issued to evse controller!'
			else:
				self.deactivate()
				print 'Disable command is issued to evse controller!'

			print('Request to update the reported state...')
			newPayload = '{"state":{"reported":' + deltaMessage + '}}'
			self.deviceShadowInstance.shadowUpdate(newPayload, None, 5)
			print('Sent.')
		elif('present_power' in commandDict):
			present_power = commandDict['present_power'] # present power setting
			newPayload = '{"state":{"reported":' + deltaMessage + '}}'
			self.deviceShadowInstance.shadowUpdate(newPayload, None, 5)
			print('Sent.')
			command = '$SC ' + str(present_power)
			chksum = 0x00
			for idx in range(len(command)):
				chksum = chksum ^ command[idx]
			command += '*'
			command += '0x{:02x}'.format(chksum)
			command += '\r'
			global reqQueue
			reqQueue.put(command)

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
ShadowClient = None
ShadowClient = AWSIoTMQTTShadowClient("OpenEvseGate_" + utils.randomword(10))
ShadowClient.configureEndpoint(host, 8883)
ShadowClient.configureCredentials(rootCAPath, privateKeyPath, certificatePath)

# AWSIoTMQTTShadowClient configuration
ShadowClient.configureAutoReconnectBackoffTime(1, 32, 20)
ShadowClient.configureConnectDisconnectTimeout(10)  # 10 sec
ShadowClient.configureMQTTOperationTimeout(5)  # 5 sec
lwttopic = 'my/things/' + shadowName + '/shadow/update'
ShadowClient.configureLastWill(lwttopic, '{"state":{"desired":{"iotconnected":false}}}', 0)

# Connect to AWS IoT
ShadowClient.connect()

# Create a deviceShadow with persistent subscription
deviceshadow = ShadowClient.createShadowHandlerWithName(shadowName, True)
evesGate = OpenEvseGateWay(deviceshadow)
deviceshadow.shadowRegisterDeltaCallback(evesGate.ShadowCallback_Delta)

###
deviceshadow.shadowUpdate('{"state":{"desired":{"iotconnected":true}}}', None, 5)

### RAPI thread start
rapi = RAPIProc()
rapi.start()

while True:
	try:
		time.sleep(1)

	except KeyboardInterrupt: # If CTRL+C is pressed, exit cleanly:
		rapi.currEvent.set()
		time.sleep(2)
		serialport.close()
		print 'program ended!'