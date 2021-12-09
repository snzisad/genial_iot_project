import jwt
from functools import wraps
from flask import Flask, jsonify, request
from pymongo import MongoClient
import os

x_access_token = os.getenv("HEADER_KEY")
secret_key = os.getenv("SECRET_KEY")


app = Flask(__name__)
client = MongoClient(port=27017)
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
                'message' : 'Bad Request'
            }), 401

    return decorated

