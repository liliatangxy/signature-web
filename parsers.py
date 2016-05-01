#!/bin/env python
# parsers.py Lew Cohen 8/19/2015
# parse raw hex, given A Priori knowledge about how the RACM is configured
# parser returns:
# 1) a UL message type: 'SensorData', 'Alarm', 'Serial', 'Config', 'RfdtData'
# 2) a list of dictionaries {sensorId, sensorName, timestamp, value}, one
# per measurement

import math
import datetime
from racm_ul_parser import RacmUlMssg

#------------------------------------------------------------------------------
# gps_2: GPS parser: 8 byte payload, described below
# This is GPS OTA RFDT, 1st version reporting RSSI and lat/lng
# NOTE: unlike other RACM apps, there is no timestamp in payload, so we just
# return the RX Timestamp. Also the data is not in pure RACM OTA format, so
# we can't use the racmUlMssg class.
#------------------------------------------------------------------------------
def parser_gps_2(raw_hex):
   # expectedSensors is included to be similar to RACM, but not used here
   expectedSensors = [{'sensorId': 7, 'sensorType':0xFFE, 'sensorName':'gps_rssi',\
                       'sensorDesc':'GPS RFDT: lat/lng in dec deg, plus DL RSSI(dBm)'}]

   # Handle Special Case: GPS RFDT can send a deprecated alarm message
   # opcode 0x01. This message will be longer than the 8 byte GPS message, which 
   # coincidentally starts with 0x01 (at least in San Diego)
   if len(raw_hex) != 16:
      d = [{'sensorName':expectedSensors[0]['sensorName'], 'lat':0, 'lng':0, 'rssi':0}]
      return ('ERROR', d)

   # Longitude ([31:0]) 26 valid bits signed, lsbs don't care
   lng = "0x" + raw_hex[8:]
   lng = int(lng, 16) >> 6 # right shift to truncate lsbs
   
   if lng > pow(2,25):
      lng = lng - pow(2,26)                  # convert to signed, if negative
   
   lng = lng << 6                            # shift back now that you truncated lsbs
   lng = lng/1e6                             # put in decimal point
   lng = str("{0:.4f}".format(round(lng,4))) # Only 4 valid decimal places
   
   # RSSI ([38:32]) 7 bits unsigned
   rssi = "0x" + raw_hex[6:8]
   rssi = int(rssi, 16) & int("0x7f", 16)    # bit mask to get 7 bit field
   rssi = -rssi - 20                         # correct the offset(add 20) and absval the rfdt applied
   
   # Latitude ([63:39]) 25 valid bits signed
   lat = "0x" + raw_hex[0:8]                 # note this is a 32 bit slice, including some RSSI in the lsbits
   lat = int(lat, 16)>>7
   if lat > pow(2,24):
      lat = lat - pow(2,25)                  # convert to signed, if negative
   
   lat = lat << 7                            # shift back now that you truncated lsbs
   lat = lat/1e6                             # put in decimal point
   lat = str("{0:.4f}".format(round(lat,4))) # Only 4 valid decimal places

   d = [{'sensorName':expectedSensors[0]['sensorName'], 'lat':lat, 'lng':lng, 'rssi':rssi}]
   return ('RfdtData', d)

#------------------------------------------------------------------------------
# Intrusion Detection + Internal K20 Temp
# Sensor Config (see RACM document for sensorType):
# APP_INTF1 (sensorID 0, J207 pin 4) is a normally closed pulled up switch for intrusion detection
#    we can alarm as well as send scheduled data on this (active high alarm).
# APP_INTF5 (sensorID 4) is K20 internal temperature, scheduled reads only
# Note this is Patrick's :u
# to enable battery powered devices to alarm asychronously (different than the document)
# The EXT_SWITCH_FUNCTION is set to alarm for testing the alarm by pushing the 
# "interrupt" switch
#------------------------------------------------------------------------------
def parser_intrusion_detector_1(raw_hex):
   expectedSensors = [{'sensorId': 0, 'sensorType':0x090, 'sensorName':'intrusion',\
                       'sensorDesc':'Intrusion Detector Switch, active high in lsbit'},
                      {'sensorId': 4, 'sensorType':0x051, 'sensorName':'temp_c',\
                       'sensorDesc':'RACM CPU Temperature (deg C)'}]
   expectedAlarmTypes = ['AppIntf1']

   msg = RacmUlMssg(raw_hex, expectedSensors, expectedAlarmTypes)
   if msg.getStatus() == 'OK':
      if msg.getMsgType() == 'Alarm':
         return(msg.getMsgType(), msg.getAlarmData())
      else:
         return(msg.getMsgType(), msg.getData())
   else:
      # Debug
      print 'ERROR: ', msg.getError()
      print 'SensorInfo: ', msg.getSensorInfo()
      print 'raw_hex = ', raw_hex
      return('ERROR','')

#------------------------------------------------------------------------------
# Intrusion Detection + Internal K20 Temp
# Sensor Config (see RACM document for sensorType):
# APP_INTF2 (sensorID 1) is a normally open pulled up switch for intrusion detection
#    we can alarm as well as send scheduled data on this (active low alarm).
# APP_INTF5 (sensorID 4) is K20 internal temperature, scheduled reads only
# Note this is Lew's version using wake from sleep on APP INTF2 J207 pin 6
# to enable battery powered devices to alarm asychronously (different than the document)
# The EXT_SWITCH_FUNCTION is set to alarm for testing the alarm by pushing the 
# "interrupt" switch
#------------------------------------------------------------------------------
def parser_intrusion_detector_2(raw_hex):
   expectedSensors = [{'sensorId': 1, 'sensorType':0x090, 'sensorName':'intrusion',\
                       'sensorDesc':'Intrusion Detector Switch, active low in lsbit'},
                      {'sensorId': 4, 'sensorType':0x051, 'sensorName':'temp_c',\
                       'sensorDesc':'RACM CPU Temperature (deg C)'}]
   expectedAlarmTypes = ['AppIntf2']

   msg = RacmUlMssg(raw_hex, expectedSensors, expectedAlarmTypes)
   if msg.getStatus() == 'OK':
      if msg.getMsgType() == 'Alarm':
         return(msg.getMsgType(), msg.getAlarmData())
      else:
         return(msg.getMsgType(), msg.getData())
   else:
      # Debug
      print 'ERROR: ', msg.getError()
      print 'SensorInfo: ', msg.getSensorInfo()
      print 'raw_hex = ', raw_hex
      return('ERROR','')

#------------------------------------------------------------------------------
# Omega 4-20mA Temperature (F) and Humidity % 
# 15 minute measurement data on both sensors. No OTA alarms
# APP_INTF5 (sensorID 4, J207 pin 13, ADC Block2) is Percent Humidity
# APP_INTF6 (sensorID 5, J207 pin  5, ADC Block1) is Degrees Fahrenheit
#------------------------------------------------------------------------------
def parser_temperature_humidity_1(raw_hex):
   expectedSensors = [{'sensorId': 4, 'sensorType':0x0B0, 'sensorName':'humidity',\
                       'sensorDesc':'Relative Humidity, 4-20mA Omega'},
                      {'sensorId': 5, 'sensorType':0x050, 'sensorName':'temp_f',\
                       'sensorDesc':'Temperature (deg F), 4-20mA Omega'}]
   expectedAlarmTypes = [] # no alarms from this device

   msg = RacmUlMssg(raw_hex, expectedSensors, expectedAlarmTypes)
   if msg.getStatus() == 'OK':
      if msg.getMsgType() == 'Alarm':
         return(msg.getMsgType(), msg.getAlarmData())
      else:
         return(msg.getMsgType(), msg.getData())
   else:
      # Debug
      print 'ERROR: ', msg.getError()
      print 'SensorInfo: ', msg.getSensorInfo()
      print 'raw_hex = ', raw_hex
      return('ERROR','')

#------------------------------------------------------------------------------
# Serial Uplink
# APP_INTF7 Application UART A_UART_RX J207 pin 7
#------------------------------------------------------------------------------
def parser_serial_1(raw_hex):
   expectedSensors = [{'sensorId': 6, 'sensorType':0xFFF, 'sensorName':'serial',\
                       'sensorDesc':'Serial, ASCII, 461 or fewer characters'}]
   expectedAlarmTypes = [] # no alarms from this device

   msg = RacmUlMssg(raw_hex, expectedSensors, expectedAlarmTypes)
   if msg.getStatus() == 'OK':
      if msg.getMsgType() == 'Alarm':
         return(msg.getMsgType(), msg.getAlarmData())
      else:
         return(msg.getMsgType(), msg.getData())
   else:
      # Debug
      print 'ERROR: ', msg.getError()
      print 'raw_hex = ', raw_hex
      return('ERROR','')


#------------------------------------------------------------------------------
# Pulse Counter 
# Default rACM15 minute measurement data. OTA alarm generated by pushbutton INT
# or using the Reed Switch. APP_INTF1 (sensorID 0) type 0x12 32-bit unsigned 
# counts.
#------------------------------------------------------------------------------
def parser_pulse_1(raw_hex):
   expectedSensors = [{'sensorId': 0, 'sensorType':0x012, 'sensorName':'pulse_counter',\
                       'sensorDesc':'K20 LPT configured to count pulses'}]
   expectedAlarmTypes = [] # no alarms from this device

   msg = RacmUlMssg(raw_hex, expectedSensors, expectedAlarmTypes)
   if msg.getStatus() == 'OK':
      if msg.getMsgType() == 'Alarm':
         return(msg.getMsgType(), msg.getAlarmData())
      else:
         return(msg.getMsgType(), msg.getData())
   else:
      # Debug
      print 'ERROR: ', msg.getError()
      print 'SensorInfo: ', msg.getSensorInfo()
      print 'raw_hex = ', raw_hex
      return('ERROR','')

#------------------------------------------------------------------------------
# KZCO Demo #1. Generic ADC parser for ANA_IN0, on dedicated APP_INTF6, and 
# undefined sensor attached to APP_INTF1 (at least for now), but will still
# need to handle the 4.8 minute UI Ota reporting.
#------------------------------------------------------------------------------
def parser_KZCO_1(raw_hex):
   expectedSensors = [{'sensorId': 0, 'sensorType':0x012, 'sensorName':'LPT',\
                       'sensorDesc':'LPT on APP_INTF_0 pin'},
                      {'sensorId': 5, 'sensorType':0x035, 'sensorName':'ANA_IN0',\
                       'sensorDesc':'ADC1 on fixed APP_INTF_6 pin'}]
   expectedAlarmTypes = ['AppIntf6'] 

   msg = RacmUlMssg(raw_hex, expectedSensors, expectedAlarmTypes)
   if msg.getStatus() == 'OK':
      if msg.getMsgType() == 'Alarm':
         return(msg.getMsgType(), msg.getAlarmData())
      else:
         return(msg.getMsgType(), msg.getData())
   else:
      # Debug
      print 'ERROR: ', msg.getError()
      print 'SensorInfo: ', msg.getSensorInfo()
      print 'raw_hex = ', raw_hex
      return('ERROR','')

  
#------------------------------------------------------------------------------

if __name__ == '__main__':
   # Test playloads... Uncomment/comment out as needed.

   #--------------------------------------------------------
   # Ingenu test payloads
   #--------------------------------------------------------
   #print 'Normally Open Intrusion Example.'
   #print parser_intrusion_detector_2('0602010902010000AB3E01140502010000AB3E1A')
   #print 'Normally Open Intrusion Alarm Example.'
   #print parser_intrusion_detector_2('0801b855b040000d00206976')
   #print 'Serial Example.'
   #print parser_serial_1('07060061626364656600')
   #print 'Pulse Counter Example'
   #print parser_pulse_1('060120010F01A922D4003000000')

   #--------------------------------------------------------
   # Paylods from KZCO  
   #--------------------------------------------------------
   # Every 5 minutes reporting (undefined sensor connection)
   print parser_KZCO_1('060220010F010D25F3408400000055030F010D25F3400800')

   # Alarm set, high voltage threshold exceeded
   print parser_KZCO_1('0801C525F340010501700600003500E8030000F4010000000000000000000001')

   # Alarm clear, voltage returns low 
   print parser_KZCO_1('0801F125F340000501130000003500E8030000F4010000000000000000000001')


