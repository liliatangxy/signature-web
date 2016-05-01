# rest2console.py Pulls UL SDUs from ORW REST interface and prints to screen. 
# Pull an SDU, Look up what parser to use, Parse the SDU, For each measurement in the SDU print to screen. 

# Configure command line parser.  Make global for simplicity of access
global optparse
from optparse import OptionParser
parser = OptionParser(description = 'Example REST parser for command line.')
parser.add_option('-f','--filter',dest='bFilterDevices', 
  help='Print to screen only devices described in ''Devices.json'' file', 
  action='store_true', default=False)
parser.add_option('-n','--nodeid',dest='nodeIdToDisplay', 
  help='Print only this node specified by the hexadecimal node ID', default='0x0')
(options, args) = parser.parse_args() 

import sys
import time
import datetime
import json
from sendStream2Console import * 
from getNextUlSdu import getNextUlSdu
from getNextUlSdu import incrementNextUlSduPointer
from getDeviceInfo import getDeviceInfo
import parsers
from restUtils import *
import pdb

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
         print 'rest2console.py: assuming downlinkDatagramResponse (or non-uplink mssg), incrementing nextUlSdu'
         incrementNextUlSduPointer(nextSduFile, last_sdu_id)
      else:
         (sdu_id, node_id_hex, rx_timestamp, payload) = getSduInfo(sdu_list)     
         (match_found, dev_info) = getDeviceInfo(node_id_hex, devices)

         # Veto match if only a specified device is called for.
         if match_found: 
             if (int(options.nodeIdToDisplay, 16) == 0):
                 pass 
             elif int(node_id_hex, 16) != int(options.nodeIdToDisplay, 16):
                 # Veto case only single node filter is enabled.
                 # increment if we don't send to Console
                 incrementNextUlSduPointer(nextSduFile, last_sdu_id) 
                 continue 
             else:
                 pass
        
         if match_found:
             # Call a parser with the payload
             print '------------------------------------------------------------------------------\n'
             print 'Begin parsing ULSDU at %s\nparser: %s\nsdu_id: %s\nnodeId: %s\nrx_timestamp: %s\npayload: %s'\
               % (datetime.datetime.now(), dev_info['parser'], sdu_id, hex(int(node_id_hex, 16)), rx_timestamp, payload)

             # ---------------------------------------------------------------------------------------------------
             # Serial 
             # ---------------------------------------------------------------------------------------------------
             if dev_info['parser'] == 'serial_1':
                (msgType, data) = parsers.parser_serial_1(payload)
   
                # Note we do not send the test button alarm to Console, so we only accept one message type
                if msgType == 'Serial':
                   allMeasAccepted = 1 # default means Console accepted all measurements
                   for i in range(len(data)):
                      timestamp = convertToDateTime(rx_timestamp).strftime("%Y-%m-%dT%H:%M:%SZ") # format Console expects
                      text = hex2text(data[i]['data']) # convert bytes to human readable text
                      res = sendSerial2Console(dev_info['m2x_primary_key'], dev_info['m2x_device_id'],\
                                              data[i]['sensorName'], timestamp, text)
   
                   # We only increment next SDU if the current SDU made it to Console completely
                   # or in the case of certain errors
                   if allMeasAccepted:
                      incrementNextUlSduPointer(nextSduFile, last_sdu_id)

                else:
                   print 'INFO: msgType will not be sent to Console: ', msgType
                   print 'Data: ', data
                   incrementNextUlSduPointer(nextSduFile, last_sdu_id) # increment if we discard  and don't send to Console

             # ---------------------------------------------------------------------------------------------------
             # Temperature Humidity 4-20mA Omega
             # Note Over the air alarms are not used in this example code, therefore if we receive any
             # alarm messages, they are ignored. Alarms (triggers) may be implemented in Console
             # ---------------------------------------------------------------------------------------------------
             elif dev_info['parser'] == 'temperature_humidity_1':
                (msgType, data) = parsers.parser_temperature_humidity_1(payload)
                if msgType == 'SensorData':
                   allMeasAccepted = 1 # default means Console accepted all measurements
                   for i in range(len(data)):
                      timestamp = data[i]['timeStamp'].strftime("%Y-%m-%dT%H:%M:%SZ") # format Console expects
                      res = sendStream2Console(dev_info['m2x_primary_key'], dev_info['m2x_device_id'],\
                                              data[i]['sensorName'], timestamp, data[i]['data'])
   
                   # We only increment next SDU if the current SDU made it to Console completely
                   if allMeasAccepted:
                      incrementNextUlSduPointer(nextSduFile, last_sdu_id)
   
                else:
                   print 'INFO: msgType will not be send to Console: ', msgType
                   print 'INFO: Data= ',  data
                   incrementNextUlSduPointer(nextSduFile, last_sdu_id) # increment if we don't send to Console

             # ---------------------------------------------------------------------------------------------------
             # INTRUSION DETECTOR1 (Normally Closed Switch) & PROCESSOR TEMPERATURE
             # Note we re-map over the air alarm messages to sensor data, to allow triggers in Console
             # to do the alarming
             # ---------------------------------------------------------------------------------------------------
             elif dev_info['parser'] == 'intrusion_detector_1':
                (msgType, data) = parsers.parser_intrusion_detector_1(payload)
   
                # For Console testing/demo only, we convert alarm into data stream time series value. We
                # do this so Console will trigger the alarm.
                # Ignore the "interrupt" pushbutton, by not parsing those alarms
                validAlarmType = 0
                if msgType == 'Alarm' and data['alarmCnt'] != '01':
                   print 'ERROR: Greater than 1 alarm per message not supported. Not sent to Console!!! Data: ',  data
                   print 'Try increasing hysteresis so only 1 alarm is sent per SDU.'
                   incrementNextUlSduPointer(nextSduFile, last_sdu_id) # increment if we don't send to Console
                elif msgType == 'Alarm' and data['alarmType'] == 'TestButton':
                   print 'INFO: TestButton Alarm will not be sent to Console. Data: ',  data
                   incrementNextUlSduPointer(nextSduFile, last_sdu_id) # increment if we don't send to Console
                elif msgType == 'Alarm' and data['alarmType'] == 'AppIntf1'\
                   and data['digAlarmThresh']=='Active_High':
                   validAlarmType = 1
                   if data['alarmState']=='Set':
                      alarm_data = [{'sensorName':'intrusion', 'timeStamp':data['timeStamp'], 'data':1}]
                   elif data['alarmState']=='Cleared':
                      alarm_data = [{'sensorName':'intrusion', 'timeStamp':data['timeStamp'], 'data':0}]
                   data = alarm_data # overwrite data with only the stuff we need to send to Console...
                elif msgType == 'SensorData':
                   pass # SensorData is already in the correct format for sendStream2Console
                else:
                   print 'INFO: msgType will not be sent to Console: ', msgType
                   print 'INFO: Data= ',  data
                   incrementNextUlSduPointer(nextSduFile, last_sdu_id) # increment if we don't send to Console

                if msgType == 'SensorData' or validAlarmType == 1:
                   allMeasAccepted = 1 # default means Console accepted all measurements
                   for i in range(len(data)):
                      timestamp = data[i]['timeStamp'].strftime("%Y-%m-%dT%H:%M:%SZ") # format Console expects
                      res = sendStream2Console(dev_info['m2x_primary_key'], dev_info['m2x_device_id'],\
                                              data[i]['sensorName'], timestamp, data[i]['data'])
   
                   # We only increment next SDU if the current SDU made it to Console completely
                   if allMeasAccepted:
                      incrementNextUlSduPointer(nextSduFile, last_sdu_id)
   
             # ---------------------------------------------------------------------------------------------------
             # INTRUSION DETECTOR2 (Normally Open Switch) & PROCESSOR TEMPERATURE
             # Note we re-map over the air alarm messages to sensor data, to allow triggers in Console
             # to do the alarming
             # Note we invert intrusion data, too (flipBit)
             # ---------------------------------------------------------------------------------------------------
             elif dev_info['parser'] == 'intrusion_detector_2':
                (msgType, data) = parsers.parser_intrusion_detector_2(payload)
   
                # On the way into Console we convert sign of intrusion detector from active low to active high for
                # graphing (so 1=intrusion)
                if msgType == 'SensorData':
                   for i in range(len(data)):
                      if data[i]['sensorName']=='intrusion':
                         data[i]['data'] = flipBit(data[i]['data'])
   
                # For Console testing/demo only, we convert alarm into data stream time series value. We
                # do this so Console will trigger the alarm.
                elif msgType == 'Alarm' and data['alarmCnt'] != '01':
                   print 'ERROR: Greater than 1 alarm per message not supported. Not sent to Console!!! Data: ',  data
                   print 'Try increasing hysteresis so only 1 alarm is sent per SDU.'

                # Ignore the "interrupt" pushbutton, by not parsing exception alarms
                elif msgType == 'Alarm' and data['alarmType'] == 'TestButton':
                   validAlarmType = 0
                   print 'INFO: Test PushButton Alarm will not be sent to Console. Data: ',  data
                   incrementNextUlSduPointer(nextSduFile, last_sdu_id) # increment if we don't send to Console

                elif msgType == 'Alarm' and data['alarmType'] == 'AppIntf2'\
                   and data['digAlarmThresh']=='Active_Low':
                   validAlarmType = 1
                   # note inversion of data in two places below
                   if data['alarmState']=='Set':
                      alarm_data = [{'sensorName':'intrusion', 'timeStamp':data['timeStamp'], 'data':1}]
                   elif data['alarmState']=='Cleared':
                      alarm_data = [{'sensorName':'intrusion', 'timeStamp':data['timeStamp'], 'data':0}]
                   data = alarm_data # overwrite data with only the stuff we need to send to Console. Regret: has caused me much confusion
   
                else:
                   print 'INFO: msgType will not be sent to Console: ', msgType
                   print 'INFO: Data= ',  data
                   validAlarmType = 0
                   incrementNextUlSduPointer(nextSduFile, last_sdu_id) # increment if we don't send to Console

                if msgType == 'SensorData' or validAlarmType == 1:
                   allMeasAccepted = 1 # default means Console accepted all measurements
                   for i in range(len(data)):
                      timestamp = data[i]['timeStamp'].strftime("%Y-%m-%dT%H:%M:%SZ") # format Console expects
                      res = sendStream2Console(dev_info['m2x_primary_key'], dev_info['m2x_device_id'],\
                                              data[i]['sensorName'], timestamp, data[i]['data'])
   
                   # We only increment next SDU if the current SDU made it to Console completely
                   if allMeasAccepted:
                      incrementNextUlSduPointer(nextSduFile, last_sdu_id)
   
             # ---------------------------------------------------------------------------------------------------
             # GPS LAT/LNG & DOWNLINK RSSI
             # Notes:
             # 1) This is not a stream in Console. We update the device location (waypoints)
             # 2) We use the 'elevation' attribute to report DL RSSI in dBm (-132dB is edge of cell)
             # 3) We implement decimation in what is reported to Console to avoid rate limiting, we measure every 4.5
             #    seconds, and report one location every minute.
             # 4) Discard incorrect GPS values (including (0,0) means no fix)
             # ---------------------------------------------------------------------------------------------------
             elif dev_info['parser'] == 'gps_2':
                (msgType, data) = parsers.parser_gps_2(payload)

                # Rare Case of deprecated RACM alarm message (opcode 0x01)
                if msgType == 'ERROR':
                   print "ERROR: GPS dropped unexpected length. This could be a RACM alarm message ", sdu_id, rx_timestamp, payload
                   incrementNextUlSduPointer(nextSduFile, last_sdu_id)
                   allMeasAccepted = 0

                elif msgType == 'RfdtData':
                   allMeasAccepted = 1 # default means Console accepted all measurements
                   # Expect one location data but this is generalized to list of N
                   for i in range(len(data)):
                      gps_ok = isGpsValid(data[i]['lat'], data[i]['lng'])
                      nodeIdHex = hex(int(node_id_hex, 16))
                      timestamp = convertToDateTime(rx_timestamp)
                      if gps_ok:
                         should_decimate = shouldDecimate(nodeIdHex, 
                           timestamp, gpsHistoryList)
                         # KS:  No real need to decimate in console version?
                         #if not should_decimate:
                         if (1):
                            timestamp = timestamp.strftime("%Y-%m-%dT%H:%M:%SZ") # format Console expects
                            sendLocRssi2Console(dev_info['m2x_primary_key'], dev_info['m2x_device_id'],\
                                                  timestamp, data[i]['lat'], data[i]['lng'], data[i]['rssi'])
                         #else:
                         #   print "INFO: GPS dropped (decimated) to reduce rate", data[i]['sensorName'],datetime.datetime.now(),\
                         #      hex(int(node_id_hex, 16)), data[i]['lat'], data[i]['lng'], data[i]['rssi'], timestamp
                         #   incrementNextUlSduPointer(nextSduFile, last_sdu_id)
                         #   allMeasAccepted = 0
                      else:
                         print "INFO: GPS dropped due to invalid location", data[i]['sensorName'],datetime.datetime.now(),\
                            hex(int(node_id_hex, 16)), data[i]['lat'], data[i]['lng'], data[i]['rssi'], timestamp
                         incrementNextUlSduPointer(nextSduFile, last_sdu_id)
                         allMeasAccepted = 0
   
                   # We only increment next SDU if the current SDU made it to Console completely
                   # or in the case of certain errors
                   if allMeasAccepted:
                      incrementNextUlSduPointer(nextSduFile, last_sdu_id)
   
                else:
                   print 'INFO: msgType will not be send to Console: ', msgType
                   print 'INFO: Data= ',  data
                   incrementNextUlSduPointer(nextSduFile, last_sdu_id) # increment if we don't send to Console

             # ---------------------------------------------------------------------------------------------------
             # Pulse Counter 
             # Note Over the air alarms are not used in this example code, therefore if we receive any
             # alarm messages, they are ignored. Alarms (triggers) may be implemented in Console
             # ---------------------------------------------------------------------------------------------------
             elif dev_info['parser'] == 'pulse_1':
                (msgType, data) = parsers.parser_pulse_1(payload)
                if msgType == 'SensorData':
                   allMeasAccepted = 1 # default means Console accepted all measurements
                   for i in range(len(data)):
                      timestamp = data[i]['timeStamp'].strftime("%Y-%m-%dT%H:%M:%SZ") # format Console expects
                      res = sendStream2Console(dev_info['m2x_primary_key'], dev_info['m2x_device_id'],\
                                              data[i]['sensorName'], timestamp, data[i]['data'])
   
                   # We only increment next SDU if the current SDU made it to Console completely
                   if allMeasAccepted:
                      incrementNextUlSduPointer(nextSduFile, last_sdu_id)
   
                else:
                   print 'INFO: msgType will not be send to Console: ', msgType
                   print 'INFO: Data= ',  data
                   incrementNextUlSduPointer(nextSduFile, last_sdu_id) # increment if we don't send to Console

             # ---------------------------------------------------------------------------------------------------
             # KZCO demo parser 
             # ---------------------------------------------------------------------------------------------------
             elif dev_info['parser'] == 'KZCO_1':
                 (msgType, data) = parsers.parser_KZCO_1(payload)
                 if msgType == 'SensorData':
                       for i in range(len(data)):
                          timestamp = data[i]['timeStamp'].strftime("%Y-%m-%dT%H:%M:%SZ") # format Console expects
                          res = sendStream2Console(dev_info['m2x_primary_key'], dev_info['m2x_device_id'],\
                                              data[i]['sensorName'], timestamp, data[i]['data'])
   
                       incrementNextUlSduPointer(nextSduFile, last_sdu_id)

                 elif msgType == 'Alarm':
                     if data['alarmCnt'] != '01':
                         print 'ERROR: Greater than 1 alarm per message not supported. Not sent to Console!!! Data: ',  data
                         print 'Try increasing hysteresis so only 1 alarm is sent per SDU.'

                         incrementNextUlSduPointer(nextSduFile, last_sdu_id) # increment if we don't send to Console

                     elif data['alarmType'] == 'AppIntf6':
                         if data['alarmState']=='Set':
                             alarmValue = 1
                         elif data['alarmState']=='Cleared':
                             alarmValue = 0

                         timestamp = data['timeStamp'].strftime("%Y-%m-%dT%H:%M:%SZ") # format Console expects
                         res = sendStream2Console(dev_info['m2x_primary_key'], dev_info['m2x_device_id'],\
                                 'Alarm Event '+data['alarmType'], timestamp, alarmValue)

                         incrementNextUlSduPointer(nextSduFile, last_sdu_id)

                 else:
                     print 'INFO: msgType will not be send to Console: ', msgType
                     print 'INFO: Data= ',  data
                     incrementNextUlSduPointer(nextSduFile, last_sdu_id) # increment if we don't send to Console

             # ---------------------------------------------------------------------------------------------------
             # Unknown Parser
             # ---------------------------------------------------------------------------------------------------
             else:
                print "ERROR: Can't find specified parser: %s for SDU_ID:%s nodeId=%s,rx_timestamp=%s,payload=%s"\
                   % (dev_info['parser'], sdu_id, hex(int(node_id_hex, 16)), rx_timestamp, payload)
   
         else:
            if not options.bFilterDevices:
                print "INFO: No device found for sdu_id, node_id, rx_timestamp, payload: ",\
                                      sdu_id, hex(int(node_id_hex, 16)), rx_timestamp, payload
            incrementNextUlSduPointer(nextSduFile, last_sdu_id) # increment if we don't send to Console
   except KeyboardInterrupt:
      sys.exit()
