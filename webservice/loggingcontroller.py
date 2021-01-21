
import boto3
from boto3.dynamodb.conditions import Key, Attr
from datetime import timedelta

import md5

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
from datetime import datetime
from pytz import timezone
import pytz

utc = pytz.utc
eastern = timezone('US/Eastern')

class LogController():
    def __init__(self):
        self.thread = True

    @staticmethod
    def addEventLogging(userid=None, type=None, detail=' '):

        timestamp = util.millis()
        utctime = utc.localize(datetime.now())
        esttime = utctime.astimezone(eastern)
        timestring = esttime.strftime("%Y-%m-%dT%H:%M:%S")

        if(userid == None):
            userid = 'backend'
        if(type == None):
            type = ' '

        try:
            dynamodb = boto3.client('dynamodb')
            response = dynamodb.put_item(
                Item={
                    'actuator': {
                        'S': userid,
                    },
                    'eventtimestamp': {
                        'N': str(timestamp),
                    },
                    'eventdatetime': {
                        'S': timestring,
                    },
                    'event_type': {
                        'S': type,
                    },
                    'detail': {
                        'S': detail,
                    },
                },
                ReturnConsumedCapacity='TOTAL',
                TableName='eventlogging',
            )

        except:
            print('dynamoDB error in adding event logging')
            return False

        return True

    @staticmethod
    def getlogs(userid=None, type=None, starttime='', endtime='', detail='', search=''):
        try:
            print('getlog')
            dynamodb = boto3.client('dynamodb')
            response = dynamodb.scan(
                ProjectionExpression='actuator, eventtimestamp, eventdatetime, detail, event_type',
                #ProjectionExpression='actuator, timestamp, datetime, detail, event_type',
                TableName='eventlogging',
            )
            return json.dumps(response)

        except:
            print('error is happened in dynamoDB getlogging operation')
        return ""
