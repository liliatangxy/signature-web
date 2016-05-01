# NOTES:
# Simple pretty print to screen.

import time
import datetime

def sendStream2Console(primary_key, device_id, stream, timestamp, value):
    # NOTE:  In console mode, primary_key an device_id are not needed,
    # as these are M2X constructs
    print 'Stream: %s, Value: %6.3f' % (stream, value)  

def sendLocRssi2Console(primary_key, device_id, stream, lat, lon, rssi):
    print 'GPS DTrack, Lat: %s, Lon: %s, RSSI: %s [dBm]' % \
      (lat, lon, rssi) 

def sendSerial2Console(primary_key, device_id, stream, timestamp, value):
    # NOTE:  In console mode, primary_key an device_id are not needed,
    # as these are M2X constructs
    print 'Serial Stream: %s, Value: %s' % (stream, value)  


