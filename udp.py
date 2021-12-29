from socket import *
import time
import json
from pymongo import MongoClient
from random import gauss
from datetime import datetime
from uuid import uuid4

address= ( '10.42.0.174', 5000) #define server IP and port
client_socket =socket(AF_INET, SOCK_DGRAM) #Set up the Socket
client_socket.settimeout(2) #Only wait 1 second for a response

# 1,2,3 = Temp, sound, light
client = MongoClient("mongodb+srv://root:root@cluster0.1offn.mongodb.net/IOT_PROJECT?retryWrites=true&w=majority")
db = client["IOT_PROJECT"]


def retrieveData():
    sensorList = [1,2,3]
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


def saveData(output):
    output = ['23.34', '53.00', '328.00']
    all_rooms = db.room_sensor.find({}, sort = [('room_id', 1), ('sensor_id', 1)])
    date = datetime.today().strftime("%d-%m-%Y")
    time = datetime.today().strftime("%H:%M")

    room_sensor_data = []
    for room in all_rooms:
        value = gauss(0, 1)
        # room_sensor_data.append({'_id': uuid4(), 'room_id': room['room_id'], 'sensor_id': room['sensor_id'], 'date': date, 'time': time, 'value': })

    db.sensor_data.insert_many(room_sensor_data)

saveData(None)