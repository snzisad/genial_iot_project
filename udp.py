from socket import *
import time
import json
from pymongo import MongoClient
from random import gauss
from datetime import datetime, timedelta
from uuid import uuid4
from pprint import pprint
import math


address = ( '10.42.0.174', 5000) #define server IP and port
client_socket =socket(AF_INET, SOCK_DGRAM) #Set up the Socket
client_socket.settimeout(2) #Only wait 1 second for a response

# 0,1,2 = Temp, sound, light
client = MongoClient("mongodb+srv://root:root@cluster0.1offn.mongodb.net/IOT_PROJECT?retryWrites=true&w=majority")
db = client["IOT_PROJECT"]


def retrieveData():
    sensorList = [0,1,2]
    data = json.dumps(sensorList)

    client_socket.sendto( data.encode(), address) #Send the data request

    try:
        rec_data, addr = client_socket.recvfrom(2048) #Read response from arduino
        x=rec_data.decode()
        output=list(x.split('*'))
        saveData(output)
    except Exception as e:
        print("Error")
        print(e)


# def saveData(output, date):
def saveData(output):
#     output = ['21.34', '55.00', '380.00']
    print(output)
    date = datetime.today().strftime("%d-%m-%Y")
    time = datetime.today().strftime("%H:%M")

    all_room_sensors = db.room_sensor.find({}, sort = [('room_id', 1), ('sensor_id', 1)])
    all_rooms_id = list(db.rooms.find({}, {'_id': 1}, sort = [('_id', 1)]))
    
    sensor_data = [[20*math.log10(float(data)) if output.index(data) == 1 else float(data) for data in output]]
    
    for _ in all_rooms_id:
        value = gauss(0, 1)
        sensor_data.append([x+value for x in sensor_data[0]])
    

    room_sensor_data = []
    for the_sensor in all_room_sensors:  
        value = sensor_data[all_rooms_id.index({'_id': the_sensor["room_id"]})][the_sensor['sensor_id']]
        room_sensor_data.append({'_id': uuid4(), 'room_id': the_sensor['room_id'], 'sensor_id': the_sensor['sensor_id'], 'date': date, 'time': time, 'value': value, 'is_latest': True})
    
    try:

        db.sensor_data.update_many({'is_latest': True}, {'$set':{'is_latest': False}})
        db.sensor_data.insert_many(room_sensor_data)
    except Exception as e:
        print(e)

def generateDummyData():
    base = datetime.today()
    output = [23.34, 56.0, 328.00]
    db.sensor_data.delete_many({})

    for x in range(100):
        value = gauss(0, 1)
        date =  base - timedelta(days=x)
        saveData([output[0]+value, output[1]+value, output[2]+value], date.strftime("%d-%m-%Y"))



# saveData(None)
# generateDummyData()