from flask import Flask, render_template, jsonify, request, send_from_directory, make_response
import pandas as pd
import json
from pymongo import MongoClient, results
from dotenv import dotenv_values
from uuid import uuid4
from pprint import pprint


app = Flask(__name__)
app.config['SECRET_KEY'] = dotenv_values(".env")["SECRET_KEY"]
x_access_token = dotenv_values(".env")["HEADER_KEY"]

client = MongoClient(port=27017)
db = client["IOT_PROJECT"]
db_test = client["TEST_PROJECT"]


@app.route('/static/<file>')
def send_static_file(file):
    return send_from_directory('static', file)


@app.route("/")
def index():
    
    # db.rooms.find({'_id':1}, {'$set':{'name': "ZISAD"}})
    # db.rooms.delete_many({}) # delete room data
    # db.room_sensor.delete_many({}) #delete room information from room sensor
    # db.sensor_data.delete_many({}) #delete all previous data of this room
    

    # db.sensors.delete_many({})

    # db.sensors.insert_many([
    #     {'_id': 0, 'name': "Temperature"},
    #     {'_id': 1, 'name': "Pressure"},
    #     {'_id': 2, 'name': "Sound"},
    #     {'_id': 3, 'name': "Humidity"},
    # ])

    # make_response(
    #         'Could not verify',
    #         401,
    #         {'WWW-Authenticate' : 'Basic realm ="Login required !!"'}
    #     )
    return "Hi. The server is working. Great job!!"
    # return render_template('index.html', family_origin = family_origin, cart_count = len(cart))
    # pass


@app.route('/api/sensor_list', methods=["GET"])
def sensor_list():
    
    if(validateAPIRequest(request)):
        all_data = db.sensors.find()
        
        return jsonify({
            'status': True,
            'data': [data for data in all_data],
        }), 200

    else:
        return jsonify({
            'status': False,
            'message' : 'Bad Request'
        }), 403

    


@app.route('/api/add_sensor', methods=["POST"])
def add_sensor():
    
    if(validateAPIRequest(request)):
        try:
            name = request.form['name']
        except :
            return jsonify({
                'status': False,
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

    else:
        return jsonify({
            'status': False,
            'message' : 'Bad Request'
        }), 403

    

@app.route('/api/delete_sensor', methods=["DELETE"])
def delete_sensor():
    
    if(validateAPIRequest(request)):
        try:
            id = int(request.form['id'])
        except :
            return jsonify({
                'status': False,
                'message': 'Sensor id is required'
            }), 422
        
        db.sensors.delete_one({'_id': id}) #delete sensor data
        db.room_sensor.delete_many({'sensor_id': id}) #delete sensor information from room sensor
        db.sensor_data.delete_many({'sensor_id': id}) #delete all previous data of this sensor
        
        return jsonify({
            'status': True,
            'message': 'Sensor information removed successfully'
        }), 200

    else:
        return jsonify({
            'status': False,
            'message' : 'Bad Request'
        }), 403


@app.route('/api/room_list', methods=["GET"])
def room_list():
    
    if(validateAPIRequest(request)):
        rooms = db.rooms.find()
        
        return jsonify({
            'status': True,
            'data': [data for data in rooms],
        }), 200

    else:
        return jsonify({
            'status': False,
            'message' : 'Bad Request'
        }), 403

    

@app.route('/api/room_sensor_list', methods=["GET"])
def room_sensor_list():
    
    if(validateAPIRequest(request)):

        pipeline = [
            {
                "$lookup": {
                    'from': "room_sensor",
                    'localField': '_id',
                    'foreignField': 'room_id',
                    'as': "room_sensor_list",
                    'pipeline':[
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
                    "_id": -1
                }
            },
        ]

        data = db.rooms.explain("executionStats").aggregate(pipeline)
        
        return jsonify({
            'status': True,
            'data': list(data),
        }), 200


    else:
        return jsonify({
            'status': False,
            'message' : 'Bad Request'
        }), 403


@app.route('/api/add_room', methods=["POST"])
def add_room():
    
    if(validateAPIRequest(request)):
        try:
            name = request.form['name']
        except :
            return jsonify({
                'status': False,
                'message': 'Room name is required'
            }), 422

        sensor_ids = request.form.getlist('sensor_ids[]')
        if len(sensor_ids) == 0:
            return jsonify({
                'status': False,
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
            room_sensor_data.append({'_id': uuid4(), 'room_id': id, 'sensor_id': int(sensor_id)})
        
        db.room_sensor.insert_many(room_sensor_data)
        
        return jsonify({
            'status': True,
            'message': 'Room added successfully'
        }), 200

    else:
        return jsonify({
            'status': False,
            'message' : 'Bad Request'
        }), 403


@app.route('/api/update_room', methods=["PUT"])
def update_room():
    
    if(validateAPIRequest(request)):
        try:
            name = request.form['name']
        except :
            return jsonify({
                'status': False,
                'message': 'Room name is required'
            }), 422
        try:
            id = int(request.form['id'])
        except :
            return jsonify({
                'status': False,
                'message': 'Room id is required'
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
            room_sensor_data.append({'_id': uuid4(), 'room_id': id, 'sensor_id': int(sensor_id)})
        
        db.room_sensor.insert_many(room_sensor_data)
        
        return jsonify({
            'status': True,
            'message': 'Room updated successfully',
        }), 200

    else:
        return jsonify({
            'status': False,
            'message' : 'Bad Request'
        }), 403

    

@app.route('/api/delete_room', methods=["DELETE"])
def delete_room():
    
    if(validateAPIRequest(request)):
        try:
            id = int(request.form['id'])
        except :
            return jsonify({
                'status': False,
                'message': 'Room id is required'
            }), 422
        
        db.rooms.delete_many({'_id': id}) # delete room data
        db.room_sensor.delete_many({'room_id': id}) #delete room information from room sensor
        db.sensor_data.delete_many({'room_id': id}) #delete all previous data of this room
        
        return jsonify({
            'status': True,
            'message': 'Room information removed successfully'
        }), 200

    else:
        return jsonify({
            'status': False,
            'message' : 'Bad Request'
        }), 403


    
@app.route('/api/search', methods=["POST"])
def search():
    
    if(validateAPIRequest(request)):
        temp = request.form['temp']
        pressure = request.form['pressure']
        sound = request.form['sound']

        data = [1, 2, 3, 4]
        
        return jsonify({
            'status': True,
            'data' : data
        }), 200

    else:
        return jsonify({
            'status': False,
            'message' : 'Bad Request'
        }), 403

    


def validateAPIRequest(request):
    try:
        token = request.headers['x_access_token']

        if token == x_access_token:
            return True

        return False

    except Exception as e:
        print(e)
        return False

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8000)
