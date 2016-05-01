# rest2m2x.py Pulls UL SDUs from ORW REST interface and pushes data to M2X99
# Pull an SDU, Look up what parser to use, Parse the SDU, For each measurement in the SDU send it individually to M2X
# Notes: 
# 1) M2X claims it has a 1 second per stream (meas) max rate, and 1000 meas/day/IPAddr, so implement pacing
# 2) If the device is multi-sensor, need to send one message per sensor (and per timestamped measurement).
# 3) I observe the web page limit is 30 locations per GPS sensor, so I set GPS_MINUTES_TO_DECIMATE = 5

import sys
import time
import datetime
import json
from getNextUlSdu import getNextUlSdu
from getNextUlSdu import incrementNextUlSduPointer
from sendStream2M2x import sendStream2M2x
from sendLocRssi2M2x import sendLocRssi2M2x
from getDeviceInfo import getDeviceInfo
import parsers
from restUtils import *

# -------------------------------------------------------------------------------------------
# MAIN
# -------------------------------------------------------------------------------------------
# This file contains the SDU ID of the next UL SDU. It provides non-volatile storage,
# so we only fetch the latest SDUs, if this script is stopped for any reason.
nextSduFile = 'nextUlSdu.cfg'
gpsHistoryList = [] # list of dicts timestamp vs node ID for decimation

with open('ATT_Devices.json','r') as infile:
    devices = json.load(infile)
    infile.close()

while 1:
   try:
      (status, last_sdu_id, size, sdu_list) = getNextUlSdu(nextSduFile)
      if status != 'OK':
         print 'sleep on error'
         time.sleep(10) # problem, wait and try again
         print 'done sleep on error'
      elif size == 0 and last_sdu_id == '':
         time.sleep(1) # queue is empty, attempt to get latest SDUs every 1 second
      elif size == 0:
         print 'rest2m2x.py: assuming downlinkDatagramResponse (or non-uplink mssg), incrementing nextUlSdu'
         incrementNextUlSduPointer(nextSduFile, last_sdu_id)
      else:
         (sdu_id, node_id_hex, rx_timestamp, payload) = getSduInfo(sdu_list)     
         (match_found, dev_info) = getDeviceInfo(node_id_hex, devices)
         if match_found:
             # Call a parser with the payload

             # ---------------------------------------------------------------------------------------------------
             # Serial (You Must set M2X stream data type to alphanumeric when creating device in M2X)
             # ---------------------------------------------------------------------------------------------------
             if dev_info['parser'] == 'serial_1':
                print '\nBegin parsing ULSDU at %s with: serial_1, sdu_id %s \nnodeId %s rx_timestamp %s payload %s'\
                   % (datetime.datetime.now(), sdu_id, hex(int(node_id_hex, 16)), rx_timestamp, payload)
                (msgType, data) = parsers.parser_serial_1(payload)
   
                # Note we do not send the test button alarm to M2x, so we only accept one message type
                if msgType == 'Serial':
                   allMeasAccepted = 1 # default means M2X accepted all measurements
                   for i in range(len(data)):
                      timestamp = convertToDateTime(rx_timestamp).strftime("%Y-%m-%dT%H:%M:%SZ") # format m2x expects
                      text = hex2text(data[i]['data']) # convert bytes to human readable text
                      res = sendStream2M2x(dev_info['m2x_primary_key'], dev_info['m2x_device_id'],\
                                              data[i]['sensorName'], timestamp, text)
                      if res == '{"status":"accepted"}':
                         print "OK: M2X Stream Updated on ATT Servers", data[i]['sensorName'],datetime.datetime.now(),\
                            '\n text = ', text, hex(int(node_id_hex, 16))
                      else:
                         print "ERROR: M2X Stream Failed to Update on ATT Servers reason: %s" % (res)
                         print data[i]['sensorName'], timestamp, data[i]['data'], text, hex(int(node_id_hex, 16)),\
                            datetime.datetime.now()
                         # We can't let a misconfigured device block all other UL SDUs
                         # so we drop this SDU and must go back and push it to M2x in the future
                         incrementNextUlSduPointer(nextSduFile, last_sdu_id)
                         allMeasAccepted = 0
   
                   # We only increment next SDU if the current SDU made it to M2X completely
                   # or in the case of certain errors
                   if allMeasAccepted:
                      incrementNextUlSduPointer(nextSduFile, last_sdu_id)

                else:
                   print 'INFO: msgType will not be sent to M2x: ', msgType
                   print 'Data: ', data
                   incrementNextUlSduPointer(nextSduFile, last_sdu_id) # increment if we discard  and don't send to M2X

             # ---------------------------------------------------------------------------------------------------
             # Temperature Humidity 4-20mA Omega
             # Note Over the air alarms are not used in this example code, therefore if we receive any
             # alarm messages, they are ignored. Alarms (triggers) may be implemented in M2x
             # ---------------------------------------------------------------------------------------------------
             elif dev_info['parser'] == 'temperature_humidity_1':
                print '\nBegin parsing ULSDU at %s with: temperature_humidity_1, sdu_id %s \nnodeId %s rx_timestamp %s payload %s'\
                   % (datetime.datetime.now(), sdu_id, hex(int(node_id_hex, 16)), rx_timestamp, payload)
                (msgType, data) = parsers.parser_temperature_humidity_1(payload)
                if msgType == 'SensorData':
                   allMeasAccepted = 1 # default means M2X accepted all measurements
                   for i in range(len(data)):
                      timestamp = data[i]['timeStamp'].strftime("%Y-%m-%dT%H:%M:%SZ") # format m2x expects
                      res = sendStream2M2x(dev_info['m2x_primary_key'], dev_info['m2x_device_id'],\
                                              data[i]['sensorName'], timestamp, data[i]['data'])
                      if res == '{"status":"accepted"}':
                         print "OK: M2X Stream Updated on ATT Servers", data[i]['sensorName'],datetime.datetime.now(),\
                            '\n', data[i]['data'], hex(int(node_id_hex, 16))
                      else:
                         print "ERROR: M2X Stream Failed to Update on ATT Servers reason: %s" % (res)
                         print data[i]['sensorName'], timestamp, data[i]['data'], hex(int(node_id_hex, 16)),\
                            datetime.datetime.now()
                         # We can't let a misconfigured device block all other UL SDUs
                         # so we drop this SDU and must go back and push it to M2x in the future
                         incrementNextUlSduPointer(nextSduFile, last_sdu_id)
                         allMeasAccepted = 0
   
                   # We only increment next SDU if the current SDU made it to M2X completely
                   if allMeasAccepted:
                      incrementNextUlSduPointer(nextSduFile, last_sdu_id)
   
                else:
                   print 'INFO: msgType will not be send to M2x: ', msgType
                   print 'INFO: Data= ',  data
                   incrementNextUlSduPointer(nextSduFile, last_sdu_id) # increment if we don't send to M2X

             # ---------------------------------------------------------------------------------------------------
             # INTRUSION DETECTOR1 (Normally Closed Switch) & PROCESSOR TEMPERATURE
             # Note we re-map over the air alarm messages to sensor data, to allow triggers in M2X
             # to do the alarming
             # ---------------------------------------------------------------------------------------------------
             elif dev_info['parser'] == 'intrusion_detector_1':
                print '\nBegin parsing ULSDU at %s with: intrusion_detector_1, sdu_id %s \nnodeId %s rx_timestamp %s payload %s'\
                   % (datetime.datetime.now(), sdu_id, hex(int(node_id_hex, 16)), rx_timestamp, payload)
                (msgType, data) = parsers.parser_intrusion_detector_1(payload)
   
                # For M2X testing/demo only, we convert alarm into data stream time series value. We
                # do this so M2X will trigger the alarm.
                # Ignore the "interrupt" pushbutton, by not parsing those alarms
                validAlarmType = 0
                if msgType == 'Alarm' and data['alarmCnt'] != '01':
                   print 'ERROR: Greater than 1 alarm per message not supported. Not sent to M2X!!! Data: ',  data
                   print 'Try increasing hysteresis so only 1 alarm is sent per SDU.'
                   incrementNextUlSduPointer(nextSduFile) # increment if we don't send to M2X
                elif msgType == 'Alarm' and data['alarmType'] == 'TestButton':
                   print 'INFO: TestButton Alarm will not be sent to M2X. Data: ',  data
                   incrementNextUlSduPointer(nextSduFile, last_sdu_id) # increment if we don't send to M2X
                elif msgType == 'Alarm' and data['alarmType'] == 'AppIntf1'\
                   and data['digAlarmThresh']=='Active_High':
                   validAlarmType = 1
                   if data['alarmState']=='Set':
                      alarm_data = [{'sensorName':'intrusion', 'timeStamp':data['timeStamp'], 'data':1}]
                   elif data['alarmState']=='Cleared':
                      alarm_data = [{'sensorName':'intrusion', 'timeStamp':data['timeStamp'], 'data':0}]
                   data = alarm_data # overwrite data with only the stuff we need to send to m2x...
                elif msgType == 'SensorData':
                   pass # SensorData is already in the correct format for sendStream2M2x
                else:
                   print 'INFO: msgType will not be sent to M2x: ', msgType
                   print 'INFO: Data= ',  data
                   incrementNextUlSduPointer(nextSduFile, last_sdu_id) # increment if we don't send to M2X

                if msgType == 'SensorData' or validAlarmType == 1:
                   allMeasAccepted = 1 # default means M2X accepted all measurements
                   for i in range(len(data)):
                      timestamp = data[i]['timeStamp'].strftime("%Y-%m-%dT%H:%M:%SZ") # format m2x expects
                      res = sendStream2M2x(dev_info['m2x_primary_key'], dev_info['m2x_device_id'],\
                                              data[i]['sensorName'], timestamp, data[i]['data'])
                      if res == '{"status":"accepted"}':
                         print "OK: M2X Stream Updated on ATT Servers", data[i]['sensorName'],datetime.datetime.now(),\
                            hex(int(node_id_hex, 16))
                      else:
                         print "ERROR: M2X Stream Failed to Update on ATT Servers reason: %s" % (res)
                         print data[i]['sensorName'], timestamp, data[i]['data'], hex(int(node_id_hex, 16)),\
                            datetime.datetime.now()
                         # We can't let a misconfigured device block all other UL SDUs
                         # so we drop this SDU and must go back and push it to M2x in the future
                         incrementNextUlSduPointer(nextSduFile, last_sdu_id)
                         allMeasAccepted = 0
   
                   # We only increment next SDU if the current SDU made it to M2X completely
                   if allMeasAccepted:
                      incrementNextUlSduPointer(nextSduFile, last_sdu_id)
   
             # ---------------------------------------------------------------------------------------------------
             # INTRUSION DETECTOR2 (Normally Open Switch) & PROCESSOR TEMPERATURE
             # Note we re-map over the air alarm messages to sensor data, to allow triggers in M2X
             # to do the alarming
             # Note we invert intrusion data, too (flipBit)
             # ---------------------------------------------------------------------------------------------------
             elif dev_info['parser'] == 'intrusion_detector_2':
                print '\nBegin parsing ULSDU at %s with: intrusion_detector_2, sdu_id %s \nnodeId %s rx_timestamp %s payload %s'\
                   % (datetime.datetime.now(), sdu_id, hex(int(node_id_hex, 16)), rx_timestamp, payload)
                (msgType, data) = parsers.parser_intrusion_detector_2(payload)
   
                # On the way into M2X we convert sign of intrusion detector from active low to active high for
                # graphing (so 1=intrusion)
                if msgType == 'SensorData':
                   for i in range(len(data)):
                      if data[i]['sensorName']=='intrusion':
                         data[i]['data'] = flipBit(data[i]['data'])
   
                # For M2X testing/demo only, we convert alarm into data stream time series value. We
                # do this so M2X will trigger the alarm.
                elif msgType == 'Alarm' and data['alarmCnt'] != '01':
                   print 'ERROR: Greater than 1 alarm per message not supported. Not sent to M2X!!! Data: ',  data
                   print 'Try increasing hysteresis so only 1 alarm is sent per SDU.'

                # Ignore the "interrupt" pushbutton, by not parsing exception alarms
                elif msgType == 'Alarm' and data['alarmType'] == 'TestButton':
                   validAlarmType = 0
                   print 'INFO: Test PushButton Alarm will not be sent to M2X. Data: ',  data
                   incrementNextUlSduPointer(nextSduFile, last_sdu_id) # increment if we don't send to M2X

                elif msgType == 'Alarm' and data['alarmType'] == 'AppIntf2'\
                   and data['digAlarmThresh']=='Active_Low':
                   validAlarmType = 1
                   # note inversion of data in two places below
                   if data['alarmState']=='Set':
                      alarm_data = [{'sensorName':'intrusion', 'timeStamp':data['timeStamp'], 'data':1}]
                   elif data['alarmState']=='Cleared':
                      alarm_data = [{'sensorName':'intrusion', 'timeStamp':data['timeStamp'], 'data':0}]
                   data = alarm_data # overwrite data with only the stuff we need to send to m2x. Regret: has caused me much confusion
   
                else:
                   print 'INFO: msgType will not be sent to M2x: ', msgType
                   print 'INFO: Data= ',  data
                   validAlarmType = 0
                   incrementNextUlSduPointer(nextSduFile, last_sdu_id) # increment if we don't send to M2X

                if msgType == 'SensorData' or validAlarmType == 1:
                   allMeasAccepted = 1 # default means M2X accepted all measurements
                   for i in range(len(data)):
                      timestamp = data[i]['timeStamp'].strftime("%Y-%m-%dT%H:%M:%SZ") # format m2x expects
                      res = sendStream2M2x(dev_info['m2x_primary_key'], dev_info['m2x_device_id'],\
                                              data[i]['sensorName'], timestamp, data[i]['data'])
                      if res == '{"status":"accepted"}':
                         print "OK: M2X Stream Updated on ATT Servers", data[i]['sensorName'],datetime.datetime.now(),\
                            hex(int(node_id_hex, 16))
                      else:
                         print "ERROR: M2X Stream Failed to Update on ATT Servers reason: %s" % (res)
                         print data[i]['sensorName'], timestamp, data[i]['data'], hex(int(node_id_hex, 16)),\
                            datetime.datetime.now()
                         # We can't let a misconfigured device block all other UL SDUs
                         # so we drop this SDU and must go back and push it to M2x in the future
                         incrementNextUlSduPointer(nextSduFile, last_sdu_id)
                         allMeasAccepted = 0
   
                   # We only increment next SDU if the current SDU made it to M2X completely
                   if allMeasAccepted:
                      incrementNextUlSduPointer(nextSduFile, last_sdu_id)
   
             # ---------------------------------------------------------------------------------------------------
             # GPS LAT/LNG & DOWNLINK RSSI
             # Notes:
             # 1) This is not a stream in M2x. We update the device location (waypoints)
             # 2) We use the 'elevation' attribute to report DL RSSI in dBm (-132dB is edge of cell)
             # 3) We implement decimation in what is reported to M2X to avoid rate limiting, we measure every 4.5
             #    seconds, and report one location every minute.
             # 4) Discard incorrect GPS values (including (0,0) means no fix)
             # ---------------------------------------------------------------------------------------------------
             elif dev_info['parser'] == 'gps_2':
                print '\nBegin parsing ULSDU at %s with: gps_2, sdu_id %s \nnodeId %s rx_timestamp %s payload %s'\
                   % (datetime.datetime.now(), sdu_id, hex(int(node_id_hex, 16)), rx_timestamp, payload)
                (msgType, data) = parsers.parser_gps_2(payload)

                # Rare Case of deprecated RACM alarm message (opcode 0x01)
                if msgType == 'ERROR':
                   print "ERROR: GPS dropped unexpected length. This could be a RACM alarm message ", sdu_id, rx_timestamp, payload
                   incrementNextUlSduPointer(nextSduFile, last_sdu_id)
                   allMeasAccepted = 0

                elif msgType == 'RfdtData':
                   allMeasAccepted = 1 # default means M2X accepted all measurements
                   # Expect one location data but this is generalized to list of N
                   for i in range(len(data)):
                      gps_ok = isGpsValid(data[i]['lat'], data[i]['lng'])
                      nodeIdHex = hex(int(node_id_hex, 16))
                      timestamp = convertToDateTime(rx_timestamp)
                      if gps_ok:
                         should_decimate = shouldDecimate(nodeIdHex, 
                           timestamp, gpsHistoryList)
                         if not should_decimate:
                            timestamp = timestamp.strftime("%Y-%m-%dT%H:%M:%SZ") # format m2x expects
                            res = sendLocRssi2M2x(dev_info['m2x_primary_key'], dev_info['m2x_device_id'],\
                                                  timestamp, data[i]['lat'], data[i]['lng'], data[i]['rssi'])
                            if res == '{"status":"accepted"}':
                               print "OK: M2X Stream Updated on ATT Servers", data[i]['sensorName'],datetime.datetime.now(),\
                                  '\n', data[i]['lat'], data[i]['lng'], hex(int(node_id_hex, 16)),\
                                  data[i]['rssi'], 'dBm RSSI', timestamp
                            else:
                               print "ERROR: M2X Stream Failed to Update on ATT Servers reason: %s" % (res)
                               print data[i]['sensorName'], timestamp, data[i]['data'], text, hex(int(node_id_hex, 16)),\
                                  datetime.datetime.now()
                               # We can't let a misconfigured device block all other UL SDUs
                               # so we drop this SDU and must go back and push it to M2x in the future
                               incrementNextUlSduPointer(nextSduFile, last_sdu_id)
                               allMeasAccepted = 0
                         else:
                            print "INFO: GPS dropped (decimated) to reduce rate, not sent to ATT Servers", data[i]['sensorName'],datetime.datetime.now(),\
                               hex(int(node_id_hex, 16)), data[i]['lat'], data[i]['lng'], data[i]['rssi'], timestamp
                            incrementNextUlSduPointer(nextSduFile, last_sdu_id)
                            allMeasAccepted = 0
                      else:
                         print "INFO: GPS dropped due to invalid location , not sent to ATT Servers", data[i]['sensorName'],datetime.datetime.now(),\
                            hex(int(node_id_hex, 16)), data[i]['lat'], data[i]['lng'], data[i]['rssi'], timestamp
                         incrementNextUlSduPointer(nextSduFile, last_sdu_id)
                         allMeasAccepted = 0
   
                   # We only increment next SDU if the current SDU made it to M2X completely
                   # or in the case of certain errors
                   if allMeasAccepted:
                      incrementNextUlSduPointer(nextSduFile, last_sdu_id)
   
                else:
                   print 'INFO: msgType will not be send to M2x: ', msgType
                   print 'INFO: Data= ',  data
                   incrementNextUlSduPointer(nextSduFile, last_sdu_id) # increment if we don't send to M2X

             # ---------------------------------------------------------------------------------------------------
             # Unknown Parser
             # ---------------------------------------------------------------------------------------------------
             else:
                print "ERROR: Can't find specified parser: %s for SDU_ID:%s nodeId=%s,rx_timestamp=%s,payload=%s"\
                   % (dev_info['parser'], sdu_id, hex(int(node_id_hex, 16)), rx_timestamp, payload)
   
         else:
            print "INFO: No device found for sdu_id, node_id, rx_timestamp, payload: ",\
                                      sdu_id, hex(int(node_id_hex, 16)), rx_timestamp, payload
            incrementNextUlSduPointer(nextSduFile, last_sdu_id) # increment if we don't send to M2X
   except KeyboardInterrupt:
      sys.exit()
