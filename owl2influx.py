import re
import socket
import struct
import time
import datetime
import os.path
import sys
import threading
import argparse
from influxdb import InfluxDBClient

# Required for parsing XML to JSON
import xmltodict
import json

# InfluxDB information and credentials
__host__ = 'localhost'
__port__ = 8086
__user__ = 'admin'
__password__ = 'admin'
__dbname__ = 'owl'

# Command line arguments parsing
parser = argparse.ArgumentParser()
parser.add_argument('--nodebug', default=False, action='store_true', help="Remove debugging and verbose messages")
args = parser.parse_args()
DEBUG = not args.nodebug

# OWL networking related
OWL_GROUP='224.192.32.19'   # Adress Multicast from the OWL device
HOST = ''                   # empty : all interfaces
PORT = 22600                # Port for listening to UDP multicast
MSGBUFSIZE=8000

# Create socket
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind((HOST, PORT))

# Multicast register to group
mreq = struct.pack ("4sl", socket.inet_aton(OWL_GROUP), socket.INADDR_ANY)
s.setsockopt (socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

print('## OWL Monitor to InfluxDB, v1.0 ##')

# Spinner if enabled
from progress.spinner import PixelSpinner

def progress(threadName, delay):
        with PixelSpinner('Waiting for multicast message on port %s ' %(PORT)) as bar:
            while True:
                time.sleep(delay)
                bar.next()
try:
    if DEBUG:
        threading.Thread(target=progress, args=("Progress thread", 0.2)).start


except:
    print("Unable to start thread")

def pushData(data, seriesName, client):
        valQuery = [1]
        val = {}
        val["fields"] = data
        val["measurement"] = seriesName
        valQuery[0] = val
        client.write_points(valQuery)

client = InfluxDBClient(__host__, __port__, database=__dbname__)

# Wait for data to come
while True:
    xmlbuffer = s.recv(MSGBUFSIZE) # waiting a packet (waiting as long as s.recv is empty)
    # print(buffer) # for debug only

    jtext = xmltodict.parse(xmlbuffer)

    try:
        # Convert the string values stored to float and transform them. The total current reported
        # in the property field is incorrect (only phase 1), hence the sum of individual phases
        currentWatts_ph1 = float(jtext['electricity']['channels']['chan'][0]['curr']['#text'])
        currentWatts_ph2 = float(jtext['electricity']['channels']['chan'][1]['curr']['#text'])
        currentWatts_ph3 = float(jtext['electricity']['channels']['chan'][2]['curr']['#text'])
        currentWatts = currentWatts_ph1 + currentWatts_ph2 + currentWatts_ph3;

        wh_ph1 = float(jtext['electricity']['channels']['chan'][0]['day']['#text'])
        wh_ph2 = float(jtext['electricity']['channels']['chan'][1]['day']['#text'])
        wh_ph3 = float(jtext['electricity']['channels']['chan'][2]['day']['#text'])

        #costToday = float(jtext['electricity']['property']['day']['cost']) / 100.0
        whToday = wh_ph1 + wh_ph2 + wh_ph3 

        # Modify the JSON accordingly
        jtext['electricity']['property'] = {'current_W': currentWatts, 'whToday': whToday}

        pretty = json.dumps(jtext, sort_keys = True, indent=4)

        if DEBUG:
            print(pretty)

        print("")
        t = time.localtime()
        current_time = time.strftime("%d.%m.%y at %H:%M:%S", t)
        print('Pushing data - ' + current_time)
        print('\tCurrent now [W]: ' + str(currentWatts))
        print('\tWatt/hours today [Wh]: ' + str(whToday))

        pushData(jtext['electricity']['property'], "heat_pump", client)
    except KeyError:
        print('Parsing error, not pushing this time')
        
    pass
