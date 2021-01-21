
from datetime import timedelta

import boto3
from boto3.dynamodb.conditions import Key, Attr
import os, sys
import json

import md5

from flask import Flask, render_template, session, request, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room, \
    close_room, rooms, disconnect

from flask import redirect
from flask_login import (LoginManager, login_required, login_user,
                         current_user, logout_user, UserMixin)

from itsdangerous import (TimedJSONWebSignatureSerializer
                          as Serializer, BadSignature, SignatureExpired)

### Thread Package
import threading

from itsdangerous import URLSafeTimedSerializer

secret_key = 'secret!'

USERS = []

login_serializer = URLSafeTimedSerializer(secret_key)

###
TOKENTIMEOUTINTERVAL = 60 * 120 # secs unit

class User(UserMixin):

    ADMINLEVEL = 0
    SITELEVEL = 1
    USERLEVEL = 2

    def __init__(self, userid, email, password, level, token):
        self.id = userid
        self.email = email
        self.password = password
        self.level = level
        self.token = token

    def generate_auth_token(self, expiration=600):
        s = Serializer(secret_key, expires_in=expiration)
        token = s.dumps({'id': self.id})
        self.token = token
        try:
            dynamodb = boto3.client('dynamodb')
            response = dynamodb.update_item(
                ExpressionAttributeValues={
                    ':token': {
                        'S': token,
                    },
                },
                Key={
                    'user_id': {
                        'S': self.id,
                    },
                },
                ReturnValues='ALL_NEW',
                TableName='UserDatabase',
                UpdateExpression='SET newtoken = :token',
            )
            return True
        except:
            print('error happened in save token in dynamoDB')
        return False

    @staticmethod
    def getuserlist():
        userlist = []
        try:
            for user in USERS:
                useritem = dict()
                useritem['id'] = user.id
                useritem['email'] = user.email
                userlist.append(useritem)
        except:
            pass

        return json.dumps(userlist)

    @staticmethod
    def verify_auth_token(token):
        s = Serializer(secret_key)
        try:
            data = s.loads(token)
        except SignatureExpired:
            print('expired signature')
            return None    # valid token, but expired
        except BadSignature:
            print('bad signature')
            return None    # invalid token
        user = User.get_fromid(data['id'])
        user.generate_auth_token(TOKENTIMEOUTINTERVAL)
        return user

    @staticmethod
    def get_fromid(user_id):
        for user in USERS:
            if user.id == user_id:
                return user
        return None

    @staticmethod
    def get(email):
        """
            Static method to search the database and see if userid exists.  If it
            does exist then return a User Object.  If not then return None as
            required by Flask-Login.
        """
        # For this example the USERS database is a list consisting of
        # (user,hased_password) of users.

        for user in USERS:
            if user.email == email:
                return user
        return None

    @staticmethod
    def newuser(userid, email, password, level):
        if(User.get(email) != None):
            print('Email is already existed.')
            return False

        if(User.get_fromid(userid) != None):
            print('userid is already existed.')
            return False

        try:
            dynamodb = boto3.client('dynamodb')
            response = dynamodb.put_item(
                Item={
                    'user_id': {
                        'S': userid,
                    },
                    'Email': {
                        'S': email,
                    },
                    'password': {
                        'S': User.hash_pass(password),
                    },
                    'user_level': {
                        'N': str(level),
                    },
                    'newtoken': {
                        'S': ' ',
                    },
                },
                ReturnConsumedCapacity='TOTAL',
                TableName='UserDatabase',
            )

            USERS.append(User(userid, email, User.hash_pass(password), level, ' '))
            return True

        except:
            print('error happened in regsiter new user in dynamoDB')

        return False

    @staticmethod
    def deluser(userid, email):
        print('delete user request is executed')

        user = User.get_fromid(userid)
        if(user == None):
            print('userid is invalid.')
            return False

        print(user.email)
        print(email)
        if(user.email != email):
            print('userid and email is not matched.')
            return False

        try:
            dynamodb = boto3.client('dynamodb')
            response = dynamodb.delete_item(
                Key={
                    'user_id': {
                        'S': userid,
                    },
                },
                TableName='UserDatabase',
            )
            USERS.remove(user)
            return True

        except:
            print('error happened in regsiter new user in dynamoDB')
        return False

    @staticmethod
    def getUserDataFromDynamoDB():
        try:
            dynamodb = boto3.client('dynamodb')
            response = dynamodb.scan(
                ProjectionExpression='user_id, Email, password, user_level, newtoken',
                TableName='UserDatabase',
            )
            # print(response)
            for userinfo in response['Items']:
                user_id = userinfo['user_id']['S']
                email = userinfo['Email']['S']
                password = userinfo['password']['S']
                user_level = userinfo['user_level']['N']
                token = ' '
                if('newtoken' in userinfo):
                    token = userinfo['newtoken']['S']
                USERS.append(User(user_id, email, password, user_level, token))
        except:
            print('error in loading user data')
            pass

    @staticmethod
    def hash_pass(password):
        """
        Return the md5 hash of the password + salt
        """
        salted_password = password + secret_key
        return md5.new(salted_password).hexdigest()


