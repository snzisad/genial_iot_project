import jwt
from flask import Flask, json, jsonify, request, send_from_directory
from flask_cors import CORS
from pymongo import MongoClient
from uuid import uuid4
from pprint import pprint
from datetime import datetime, timedelta
from  werkzeug.security import generate_password_hash, check_password_hash
from Decorator import verify_request, token_required
import os


app = Flask(__name__)
CORS(app)
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")

# client = MongoClient(port=27017)
client = MongoClient("mongodb+srv://root:root@cluster0.1offn.mongodb.net/IOT_PROJECT?retryWrites=true&w=majority")
db = client["IOT_PROJECT"]

@app.route('/static/<file>')
def send_static_file(file):
    return send_from_directory('static', file)


@app.route("/")
def index():
    # db.user.delete_many({})

    # db.user.insert_one({
    #     "_id": str(uuid4()),
    #     "username": "admin",
    #     "password": generate_password_hash("123456")
    # })

    # make_response(
    #         'Could not verify',
    #         401,
    #         {'WWW-Authenticate' : 'Basic realm ="Login required !!"'}
    #     )

    # return jsonify(list(client.list_databases()))
    return "Hi. The server is working. Great job!!"
    # return render_template('index.html', family_origin = family_origin, cart_count = len(cart))
    # pass


@app.route('/api/login', methods=["POST"])
@verify_request
def login():
    request_data = request.form
    username = request_data.get('username')
    password = request_data.get('password')

    if username is None:
        return jsonify({
            'status': False,
            'error_at': 'username',
            'message': 'Username is required'
        }), 422

    if password is None:
        return jsonify({
            'status': False,
            'error_at': 'password',
            'message': 'Password is required'
        }), 422

    user = db.user.find_one({"username": username})


    if user is not None and check_password_hash(user["password"], password):
        # generates the JWT Token
        token = jwt.encode({
            'public_id': str(user["_id"]),
            'exp' : datetime.utcnow() + timedelta(minutes = 30)
        }, app.config['SECRET_KEY'])

        return jsonify({
            'status': True,
            'token' : token.decode('UTF-8')
        }), 200


    return jsonify({
        'status': False,
        'message': 'Invalid username or password'
    }), 403


@app.route('/api/sensor_list', methods=["GET"])
@token_required
def sensor_list(*_):
    data = db.sensors.find()

    return jsonify({
        'status': True,
        'data': list(data),
    }), 200




@app.route('/api/add_sensor', methods=["POST"])
@token_required
def add_sensor(*_):
    name = request.form.get('name')

    if name is None:
        return jsonify({
            'status': False,
            'error_at': 'name',
            'message': 'Sensor name is required'
        }), 422

    last_item = db.sensors.find_one({}, sort = [('_id', -1)])
    if last_item == None:
        id = 0
    else:
        id = last_item['_id']+1


    db.sensors.insert_one(
        {'_id': id, 'name': name},
    )

    return jsonify({
        'status': True,
        'message': 'Sensor added successfully'
    }), 200



@app.route('/api/delete_sensor', methods=["DELETE"])
@token_required
def delete_sensor(*_):
    id = request.form.get('id')

    if id is None :
        return jsonify({
            'status': False,
            'error_at': 'id',
            'message': 'Sensor id is required'
        }), 422

    try:
        id = int(id)
    except Exception as e:
        print(e)
        return jsonify({
            'status': False,
            'error_at': 'id',
            'message': "Room id should be integer value"
        }), 422


    db.sensors.delete_one({'_id': id}) #delete sensor data
    db.room_sensor.delete_many({'sensor_id': id}) #delete sensor information from room sensor
    db.sensor_data.delete_many({'sensor_id': id}) #delete all previous data of this sensor

    return jsonify({
        'status': True,
        'message': 'Sensor information removed successfully'
    }), 200


@app.route('/api/room_list', methods=["GET"])
@token_required
def room_list(*_):
    rooms = db.rooms.find()

    return jsonify({
        'status': True,
        'data': [data for data in rooms],
    }), 200



@app.route('/api/room_sensor_list', methods=["GET"])
@token_required
def room_sensor_list(*_):
    pipeline = [
        {
            "$lookup": {
                'from': "room_sensor",
                'as': "room_sensor_list",
                "let": { "parent_room_id": "$_id" },
                'pipeline':[
                    {
                        "$match": {
                            "$expr": {
                                "$eq": ["$room_id", "$$parent_room_id"]
                            }
                        }
                    },
                    {
                        "$lookup": {
                            'from': "sensors",
                            'as': "sensor_info",
                            "let": { "room_sensor_id": "$sensor_id" },
                            "pipeline": [
                                {
                                    "$match": {
                                        "$expr": {
                                            "$eq": ["$_id", "$$room_sensor_id"]
                                        }
                                    }
                                }
                            ],
                        }
                    }
                ],

            }
        },
        {
        "$unwind": {
            "path": "$room_sensor_list",
            "preserveNullAndEmptyArrays": True
            }
        },
        {
            "$group": {
                "_id": "$_id",
                "name": {
                    "$first": "$name"
                },
                "sensor": {
                    "$push": "$room_sensor_list.sensor_info"

                }
            }
        },
        {
            "$sort": {
                "_id": 1
            }
        },
    ]

    data = db.rooms.aggregate(pipeline)

    return jsonify({
        'status': True,
        'data': list(data),
    }), 200


@app.route('/api/add_room', methods=["POST"])
@token_required
def add_room(*_):
    name = request.form.get('name')

    if name is None :
        return jsonify({
            'status': False,
            'error_at': 'name',
            'message': 'Room name is required'
        }), 422

    sensor_ids = request.form.getlist('sensor_ids[]')
    if len(sensor_ids) == 0:
        return jsonify({
            'status': False,
            'error_at': 'sensor_ids',
            'message': 'Sensor array is required'
        }), 422

    last_item = db.rooms.find_one({}, sort = [('_id', -1)])
    if last_item == None:
        id = 0
    else:
        id = last_item['_id']+1


    db.rooms.insert_one(
        {'_id': id, 'name': name},
    )

    room_sensor_data = []
    for sensor_id in sensor_ids:
        try:
            room_sensor_data.append({'_id': uuid4(), 'room_id': id, 'sensor_id': int(sensor_id)})
        except:
            return jsonify({
                'status': False,
                'error_at': 'sensor_ids',
                'message': 'Sensor array elements must be integer'
            }), 200

    db.room_sensor.insert_many(room_sensor_data)

    return jsonify({
        'status': True,
        'message': 'Room added successfully'
    }), 200


@app.route('/api/update_room', methods=["PUT"])
@token_required
def update_room(*_):
    name = request.form.get('name')
    id = request.form.get('id')

    if name is None :
        return jsonify({
            'status': False,
            'message': 'Room name is required'
        }), 422

    if id is None:
        return jsonify({
            'status': False,
            'message': 'Room id is required'
        }), 422

    try:
        id = int(id)
    except Exception as e:
        print(e)
        return jsonify({
            'status': False,
            'error_at': 'id',
            'message': "Room id should be integer value"
        }), 422

    sensor_ids = request.form.getlist('sensor_ids[]')
    if len(sensor_ids) == 0:
        return jsonify({
            'status': False,
            'message': 'Sensor array is required'
        }), 422

    db.rooms.update_one({'_id': id}, {'$set':{'name': name}})

    db.room_sensor.delete_many({'room_id': id}) #delete room information from room sensor
    db.sensor_data.delete_many({'room_id': id}) #delete all previous data of this room

    room_sensor_data = []
    for sensor_id in sensor_ids:
        try:
            room_sensor_data.append({'_id': uuid4(), 'room_id': id, 'sensor_id': int(sensor_id)})
        except:
            return jsonify({
                'status': False,
                'error_at': 'sensor_ids',
                'message': 'Sensor array elements must be integer'
            }), 200


    db.room_sensor.insert_many(room_sensor_data)

    return jsonify({
        'status': True,
        'message': 'Room updated successfully',
    }), 200



@app.route('/api/delete_room', methods=["DELETE"])
@token_required
def delete_room(*_):
    id = request.form.get('id')

    if id is None:
        return jsonify({
            'status': False,
            'message': 'Room id is required'
        }), 422

    try:
        id = int(id)
    except Exception as e:
        print(e)
        return jsonify({
            'status': False,
            'error_at': 'id',
            'message': "Room id should be integer value"
        }), 422

    db.rooms.delete_many({'_id': id}) # delete room data
    db.room_sensor.delete_many({'room_id': id}) #delete room information from room sensor
    db.sensor_data.delete_many({'room_id': id}) #delete all previous data of this room

    return jsonify({
        'status': True,
        'message': 'Room information removed successfully'
    }), 200


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8000)
