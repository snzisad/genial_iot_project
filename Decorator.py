import jwt
from functools import wraps
from flask import Flask, jsonify, request
from flask_cors import CORS
from pymongo import MongoClient
import os

x_access_token = os.getenv("HEADER_KEY")
secret_key = os.getenv("SECRET_KEY")


app = Flask(__name__)
CORS(app)
client = MongoClient("mongodb+srv://root:root@cluster0.1offn.mongodb.net/IOT_PROJECT?retryWrites=true&w=majority")
db = client["IOT_PROJECT"]

# decorator for verifying the JWT
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        # jwt is passed in the request header
        if 'x-access-token' in request.headers:
            token = request.headers['x-access-token']
        # return 401 if token is not passed
        if not token:
            return jsonify({'message' : 'Token is missing !!'}), 401
            
        try:
            # decoding the payload to fetch the stored details
            data = jwt.decode(token, secret_key)
            current_user = db.user.find_one({"_id": data['public_id']})

            # returns the current logged in users contex to the routes
            return  f(current_user, *args, **kwargs)

        except Exception as e:
            print(e)

            return jsonify({
                'message' : 'Token is invalid !!'
            }), 401

    return decorated


# decorator for verifying the JWT or api_key
def api_key_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        # jwt is passed in the request header
        if 'x-access-token' in request.headers:
            token = request.headers['x-access-token']

            try:
                # decoding the payload to fetch the stored details
                data = jwt.decode(token, secret_key)
                current_user = db.user.find_one({"_id": data['public_id']})

                # returns the current logged in users contex to the routes
                return  f(current_user, *args, **kwargs)

            except Exception as e:
                print(e)

                return jsonify({
                    'message' : 'Token is invalid !!'
                }), 401

        elif 'api_key' in request.args:
            api_key = request.args.get("api_key")
            current_user = db.user.find_one({"api_key": api_key})

            if current_user is not None:
                return  f(current_user, *args, **kwargs)
            else:
                return jsonify({
                    'message' : 'Api key is invalid !!'
                }), 401
                
        if not token:
            return jsonify({'message' : 'Token or api key is required !!'}), 401
            
    return decorated


# decorator for verifying the request
def verify_request(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'x-access-token' in request.headers:
            token = request.headers['x-access-token']

            if not token:
                return jsonify({'message' : 'Bad Request'}), 401

            if token == x_access_token:
                return  f(*args, **kwargs)

            else:
                return jsonify({
                    'message' : 'Token is invalid !!'
                }), 401

        elif 'api_key' in request.args:
            api_key = request.args.get("api_key")
            current_user = db.user.find_one({"api_key": api_key})

            if current_user is not None:
                return  f(current_user, *args, **kwargs)
            else:
                return jsonify({
                    'message' : 'Api key is invalid !!'
                }), 401
             
        return jsonify({
            'message' : 'Bad Request'
        }), 401

    return decorated

