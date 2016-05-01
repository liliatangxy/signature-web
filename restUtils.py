import time
import datetime

# shared utility functions for the rACM to REST demo
def getSduInfo(sdu_list):
    sdu = sdu_list[0] # note we receive a list of lists, but it only contains 1 sdu
    sdu_id = sdu[0]
    payload = sdu[1]
    node_id_hex = sdu[2] # NOTE: Looks like after intellect 1.0.7-4, its now hex! 
    rx_timestamp = sdu[3]
    return(sdu_id, node_id_hex, rx_timestamp, payload)

# Invert a one bit binary number
def flipBit(input):
   if input == 0:
      output = 1
   elif input == 1:
      output = 0
   else:
      output = input
   return output

# Convert date from REST IF (string) to python datetime, and change timezone to GMT
#   input date format      = '2015-08-10T17:14:20-07:00'
def convertToDateTime(input_date):
   # Strip off decimal part of seconds, if it is there
   a = input_date.find('.')
   if a != -1:
      input_date = input_date[:a] + input_date[a+7:]
   # Small conversion on input time to handle timezone, python can't
   # if there is an appended timezone (ex. "-07:00")
   if len(input_date)==25:
      tzHours = int(input_date[-6:-3])
      input_date = input_date[0:-6]
   elif len(input_date)==20 and input_date[-1:]=='Z':
      input_date = input_date[0:-1]
      tzHours = 0
   else:
      print 'WARNING: unexpected date format in rest2console.py', input_date
      tzHours = 0

   # Python doesn't have datetime.strptime (my version 2.6.6)
   input_t = time.strptime(input_date, '%Y-%m-%dT%H:%M:%S')
   # some hoops you have to jump through in python:
   input_dt = datetime.datetime.fromtimestamp(time.mktime(input_t))
   input_dt = input_dt - datetime.timedelta(hours=tzHours)
   return input_dt

# Convert a hexadicamal string of form '656667' to text 'ABC'
# for use displaying serial input
def hex2text(hex_string):
   txt_string = ''
   hasIllegalChar = 0
   for i in range(len(hex_string)/2):
      byte = hex_string[2*i:2*i+2]
      ascval = int(byte, 16)
      # Note we skip illegal characters to avoid JSON UTF-8 errors
      if ascval <= 127:
         txt_string += chr(ascval)
      else:
         hasIllegalChar = 1

   if hasIllegalChar:
      print 'ERROR: serial text contains illegal characters(ASCII value > 127), check baud rate'
   return txt_string
      
# Should I decimate this GPS?
#   - timestamp is a datetime
def shouldDecimate(nodeIdHex, timestamp, gpsHistoryList):
   GPS_MINUTES_TO_DECIMATE = 5
   must_decimate = 0
   node_in_list = 0

   for d in gpsHistoryList:
      if d['nodeIdHex'] == nodeIdHex:
         node_in_list = 1
         if timestamp - d['timestamp'] <= datetime.timedelta(seconds=0):
            must_decimate = 1
         else:
            # Because gpsHistoryList is mutable, this will update 
            # the timestamp of the node in gpsHistoryList
            # to this timestamp plus 1 minute
            d['timestamp'] = timestamp + datetime.timedelta(minutes=GPS_MINUTES_TO_DECIMATE)

   if not node_in_list:
      next_timestamp = timestamp + datetime.timedelta(minutes=GPS_MINUTES_TO_DECIMATE)
      gpsHistoryList.append({'nodeIdHex':nodeIdHex, 'timestamp':next_timestamp})
       
   return must_decimate

# Return 1 if GPS is non-zero and in range
# This simple function is biased toward no false readings in US
# It rejects England, and many other places...
def isGpsValid(lat, lng):
   lat = float(lat)
   lng = float(lng)
   gps_valid = 1
   if lat < 1 and lat > -1:
      gps_valid = 0
   if lng < 1 and lng > -1:
      gps_valid = 0
   if lat > 89 or lat < -89:
      gps_valid = 0
   if lng > 179 or lng < -179:
      gps_valid = 0
   return gps_valid

