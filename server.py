from calendar import prmonth
from itertools import count
import jwt
from flask import Flask, json, jsonify, request, send_from_directory
from flask_cors import CORS
from pymongo import MongoClient
from uuid import uuid4
from pprint import pprint
from datetime import datetime, timedelta
from  werkzeug.security import generate_password_hash, check_password_hash
from Decorator import verify_request, token_required, api_key_required
from udp import retrieveData
import os

# 10.42.0.174

app = Flask(__name__)
CORS(app)
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")

# client = MongoClient(port=27017)
client = MongoClient("mongodb+srv://root:root@cluster0.1offn.mongodb.net/IOT_PROJECT?retryWrites=true&w=majority")
db = client["IOT_PROJECT"]

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


@app.route('/api/register', methods=["POST"])
@verify_request
def register():
    request_data = request.form
    email = request_data.get('email')
    password = request_data.get('password')
    role = request_data.get('role')

    if email is None:
        return jsonify({
            'status': False,
            'error_at': 'email',
            'message': 'Email is required'
        }), 422

    if password is None:
        return jsonify({
            'status': False,
            'error_at': 'password',
            'message': 'Password is required'
        }), 422

    if role is None:
        return jsonify({
            'status': False,
            'error_at': 'role',
            'message': 'Role is required'
        }), 422

    user = db.user.find_one({"email": email})

    if user is None:
        api_key = str(uuid4()).replace('-', '')

        db.user.insert_one({
            "_id": str(uuid4()),
            "email": email,
            "role": role,
            "api_key": api_key,
            "password": generate_password_hash(password)
        })

        return jsonify({
            'status': True,
            'api_key': api_key
        }), 200

    else:
        return jsonify({
            'status': False,
            'message': 'User already exixts'
        }), 409


@app.route('/api/login', methods=["POST"])
@verify_request
def login():
    request_data = request.form
    email = request_data.get('email')
    password = request_data.get('password')
    role = request_data.get('role')

    if email is None:
        return jsonify({
            'status': False,
            'error_at': 'email',
            'message': 'Email is required'
        }), 422

    if password is None:
        return jsonify({
            'status': False,
            'error_at': 'password',
            'message': 'Password is required'
        }), 422

    if role is None:
        return jsonify({
            'status': False,
            'error_at': 'role',
            'message': 'Role is required'
        }), 422

    user = db.user.find_one({"email": email, "role": role})


    if user is not None and check_password_hash(user["password"], password):
        # generates the JWT Token
        token = jwt.encode({
            'public_id': str(user["_id"]),
            'exp' : datetime.utcnow() + timedelta(minutes = 7*24*60)
        }, app.config['SECRET_KEY'])

        return jsonify({
            'status': True,
            'api_key': user["api_key"],
            'token' : token.decode('UTF-8')
        }), 200


    return jsonify({
        'status': False,
        'message': 'Invalid email, password or role'
    }), 403


@app.route('/api/sensor_list', methods=["GET"])
@api_key_required
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

    sensor = db.sensors.find_one({"name": name})
    if sensor is not None:
        return jsonify({
            'status': False,
            'message': 'This sensor is already added'
        }), 409


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
@api_key_required
def room_list(*_):
    rooms = db.rooms.find()

    return jsonify({
        'status': True,
        'data': [data for data in rooms],
    }), 200


@app.route('/api/room_sensor_list', methods=["GET"])
@verify_request
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

    room = db.rooms.find_one({"name": name})
    if room is not None:
        return jsonify({
            'status': False,
            'message': 'This room is already added'
        }), 409

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
            sensor_data = db.sensors.find_one({"_id": int(sensor_id)})
            if sensor_data is not None:
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
    # db.sensor_data.delete_many({'room_id': id}) #delete all previous data of this room
    # db.sensor_data.remove( { 'room_id': id, 'sensor_id' : { '$nin': sensor_ids } } )

    room_sensor_data = []
    for sensor_id in sensor_ids:
        try:
            sensor_data = db.sensors.find_one({"_id": int(sensor_id)})
            if sensor_data is not None:
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



@app.route('/api/room_ranking', methods=["GET"])
@verify_request
def room_ranking(*_):
    retrieveData()
    rooms = list(db.rooms.find({}, sort = [('_id', 1)]))
    room_points = {}
    
    for i, room in enumerate(rooms):
        sensors = list(db.room_sensor.find({"room_id": room["_id"]}, {'_id': 0, 'sensor_id': 1}, sort = [("_id", -1)]))
        room_sensor_data = []

        comfort_pass_num = 0

        for sensor in sensors:
            sensor_id = sensor["sensor_id"]
            sensor_info = db.sensors.find_one({"_id": sensor_id})
            sensor_data = db.sensor_data.find_one({"room_id": room["_id"], "sensor_id": sensor_id, "is_latest": True})            
            
            value = sensor_data["value"]
            sensor_info.update({'value': value})

            if sensor_id == 0 and value>=18 and value <= 23:
                comfort_pass_num = comfort_pass_num+1
            elif sensor_id == 1 and value<30:
                comfort_pass_num = comfort_pass_num+1
            elif sensor_id == 2 and value>=100 and value <= 300:
                comfort_pass_num = comfort_pass_num+1

            room_sensor_data.append(sensor_info)
        
        points = 0.333*comfort_pass_num
        room_points.update({i: points})
        room.update({'sensor': room_sensor_data})
        room.update({'points': points*100})

    room_points = {k: v for k, v in sorted(room_points.items(), key=lambda item: item[1],  reverse=True)}
    selected_room_pos = room_points.keys()

    return jsonify({
        'status': True,
        'data': [rooms[index] for index in selected_room_pos],
    }), 200



@app.route('/api/room_sensor_data', methods=["GET"])
@verify_request
def room_sensor_data(*_):
    retrieveData()
    rooms = list(db.rooms.find({}, sort = [('_id', 1)]))
    for room in rooms:
        sensors = db.room_sensor.find({"room_id": room["_id"]}, {'_id': 0, 'sensor_id': 1})
        room_sensor_data = []
        for sensor in sensors:
            sensor_info = db.sensors.find_one({"_id": sensor["sensor_id"]})
            sensor_data = db.sensor_data.find({"room_id": room["_id"], "sensor_id": sensor["sensor_id"]})
            values = []
            dates = []
            times = []
            for data in sensor_data:
                values.append(data["value"])
                dates.append(data["date"])
                times.append(data["time"])
            
            sensor_info.update({'values': values})
            sensor_info.update({'dates': dates})
            sensor_info.update({'times': times})

            room_sensor_data.append(sensor_info)

        room.update({'sensor': room_sensor_data})
    
    return jsonify({
        'status': True,
        'data': rooms,
    }), 200


@app.route('/api/room_wise_data', methods=["GET"])
@verify_request
def room_wise_data(*_):
    retrieveData()
    if 'room_id' not in request.args:
        return jsonify({
            'status': False,
            'message': "Room id is required",
        }), 422

    try:
        room_id = int(request.args.get("room_id"))
    except:
        return jsonify({
            'status': False,
            'message': "Room id should be integer value",
        }), 422


    room = db.rooms.find_one({"_id": room_id})
    sensors = db.room_sensor.find({"room_id": room["_id"]}, {'_id': 0, 'sensor_id': 1}, sort = [('sensor_id', 1)])
    room_sensor_data = []
    for sensor in sensors:
        sensor_info = db.sensors.find_one({"_id": sensor["sensor_id"]})
        sensor_data = db.sensor_data.find({"room_id": room["_id"], "sensor_id": sensor["sensor_id"]})
        values = []
        dates = []
        times = []
        for data in sensor_data:
            values.append(data["value"])
            dates.append(data["date"])
            times.append(data["time"])
        
        sensor_info.update({'values': values})
        sensor_info.update({'dates': dates})
        sensor_info.update({'times': times})

        room_sensor_data.append(sensor_info)

    room.update({'sensor': room_sensor_data})

    return jsonify({
        'status': True,
        'data': room,
    }), 200


@app.route('/api/sensor_wise_data', methods=["GET"])
@verify_request
def sensor_wise_data(*_):
    retrieveData()
    if 'sensor_id' not in request.args:
        return jsonify({
            'status': False,
            'message': "Sensor id is required",
        }), 422

    try:
        sensor_id = int(request.args.get("sensor_id"))
    except:
        return jsonify({
            'status': False,
            'message': "Sensor id should be integer value",
        }), 422

    rooms = list(db.rooms.find({}, sort = [('_id', 1)]))
    for room in rooms:
        sensors = db.room_sensor.find({"room_id": room["_id"], "sensor_id": sensor_id}, {'_id': 0, 'sensor_id': 1})
        room_sensor_data = []
        for sensor in sensors:
            sensor_info = db.sensors.find_one({"_id": sensor["sensor_id"]})
            sensor_data = db.sensor_data.find({"room_id": room["_id"], "sensor_id": sensor["sensor_id"]})
            values = []
            dates = []
            times = []
            for data in sensor_data:
                values.append(data["value"])
                dates.append(data["date"])
                times.append(data["time"])
            
            sensor_info.update({'values': values})
            sensor_info.update({'dates': dates})
            sensor_info.update({'times': times})

            room_sensor_data.append(sensor_info)

        room.update({'sensor': room_sensor_data})

    return jsonify({
        'status': True,
        'data': rooms,
    }), 200


@app.route('/api/date_wise_data', methods=["GET"])
@verify_request
def date_wise_data(*_):
    retrieveData()
    if 'from_date' not in request.args:
        return jsonify({
            'status': False,
            'message': "From date is required",
        }), 422

    if 'to_date' not in request.args:
        return jsonify({
            'status': False,
            'message': "To date is required",
        }), 422


    from_date = request.args.get("from_date")
    to_date = request.args.get("to_date")

    rooms = list(db.rooms.find({}, sort = [('_id', 1)]))
    for room in rooms:
        sensors = db.room_sensor.find({"room_id": room["_id"]}, {'_id': 0, 'sensor_id': 1})
        room_sensor_data = []
        for sensor in sensors:
            sensor_info = db.sensors.find_one({"_id": sensor["sensor_id"]})
            sensor_data = db.sensor_data.find({"room_id": room["_id"], "sensor_id": sensor["sensor_id"], "date": {'$gte': from_date, '$lte':to_date}})
            values = []
            dates = []
            times = []
            for data in sensor_data:
                values.append(data["value"])
                dates.append(data["date"])
                times.append(data["time"])
            
            sensor_info.update({'values': values})
            sensor_info.update({'dates': dates})
            sensor_info.update({'times': times})

            room_sensor_data.append(sensor_info)

        room.update({'sensor': room_sensor_data})

    return jsonify({
        'status': True,
        'data': rooms,
    }), 200



if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8000)
