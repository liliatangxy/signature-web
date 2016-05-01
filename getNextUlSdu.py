#!/bin/env python
# getNextUlSdu.py Lew Cohen 10/16/2015
# Pull one UL SDU from REST interface
# Note as of this writing m2x only accepts one write per second per device
# which influences why we only pull 1 SDU
# We also need to be concerned to not duplicate sdus into the m2x database
# This script uses nextUlSdu.cfg to keep track of next messageId 
# 2/15/2016 The terminology has changed from SDUs to messages, may not be fully reflected in
# variable names
# Note: we believe this default messageId corresponds to a config response from
# racm 0x304b1 (197809) sent 2-29-2016 21:43:31 GMT on ingenudemo REST
# messageId = 1e095a80-df2d-11e5-8fe9-0380bd1c3ac8 

import sys
import httplib
from getLoginInfo import getLoginInfo
from xml.dom import minidom
from xml.parsers.expat import ExpatError

#------------------------------------------------------------------------------
# CONSTANTS and CONFIG:
#------------------------------------------------------------------------------
max_results = 1 # normally should be 1000 but for m2x limitation, this simplifies

# Get REST Login Info from a file
(host, username, password) = getLoginInfo("login_info.json")
rest_headers = {"Username": username, "Password": password, "Accept":"application/xml"}

# Note you can append to this url:
# messageId: this will pull only mssgs AFTER the appended messageID (last one you received)
# count: "?count=10" will return 10 mssgs. Max/Default = 500
data_url = "/data/v1/receive"

#------------------------------------------------------------------------------
# Pull The Next SDU From REST Interface 
#------------------------------------------------------------------------------
def pullUlSdu (start_sdu_id):
   sdus = [] # init
   # Note the SDUs get appended to global list of lists sdus in parseResults
   size = max_results # initialize so while loop runs at least one time
   url  = data_url
   if start_sdu_id != '':
      url = url + '/' + start_sdu_id
   url = url.replace('\n','').replace('\r','') # make sure no carriage return/line feed
   url = url + '?count=1'

   # predefine these variables for the exception case (avoids nastygram)
   response = 'No Info'
   result = 'No Info'
   dom = 'No Info'

   try:
      rest_conn.request("GET", url, "", rest_headers)
      response = rest_conn.getresponse() # sometimes fails with BadStatusLine or CannotSendRequest
      result = response.read()
      dom = minidom.parseString(result)
      (last_sdu_id, sdus) = parseResults(dom, sdus)
      size = len(sdus)
      return ('OK', last_sdu_id, size, sdus)
   except:
      print 'ERROR(pullUlSdu): ', sys.exc_info()[:2]
      print 'url ', url, 'rest_headers ', rest_headers
      print 'response= ', response # 'This method may not be used.'
      print 'result = ', result
      print 'dom = ', dom
      rest_conn.close() # This line helps with BadStatusLine error recovery
      # added 2 dummy return values at end to match success case
      return ('ERROR', str(sys.exc_info()[0]),'','')

#------------------------------------------------------------------------------
# Parses the REST ULSDU Query Results (XML)
#------------------------------------------------------------------------------
def parseResults(dom, sdus):
   ul_elements = dom.getElementsByTagName("uplink")
   last_sdu_id = ''
   for ul in ul_elements:
      sdu_id = ul.getElementsByTagName("messageId")[0].childNodes[0].nodeValue
      messageType = ul.getElementsByTagName("messageType")[0].childNodes[0].nodeValue # future use
      if messageType == 'DatagramUplinkEvent':
         datagramContents = ul.getElementsByTagName("datagramUplinkEvent")[0]
         raw_hex = datagramContents.getElementsByTagName("payload")[0].childNodes[0].nodeValue
         node_id = datagramContents.getElementsByTagName("nodeId")[0].childNodes[0].nodeValue
         timestamp = datagramContents.getElementsByTagName("timestamp")[0].childNodes[0].nodeValue
         sdus.append([sdu_id, raw_hex, node_id, timestamp])
      elif messageType == 'DatagramDownlinkResponse':
         datagramContents = ul.getElementsByTagName("datagramDownlinkResponse")[0]
         node_id = datagramContents.getElementsByTagName("nodeId")[0].childNodes[0].nodeValue
         timestamp = datagramContents.getElementsByTagName("timestamp")[0].childNodes[0].nodeValue
         status = datagramContents.getElementsByTagName("status")[0].childNodes[0].nodeValue
         tag = datagramContents.getElementsByTagName("tag")[0].childNodes[0].nodeValue
         print 'getNextUlSdu.py: Downlink Status (no further action) ', node_id, timestamp, status,\
            'tag = ', tag, 'messageId = ', sdu_id
      else:
         print 'getNextUlSdu.py: No action taken on messageType: ', messageType

      last_sdu_id = sdu_id # increment to get next message from REST
   return (last_sdu_id, sdus)

#------------------------------------------------------------------------------
# Gets the messageId of the previous message from a file
# NOTE: You should store the previousMessageId in non-volatile (ex. disk) memory
# so that when your program is restarted, you don't fetch lots of old data
#------------------------------------------------------------------------------
# Comment: LEW Clean up naming. It is unclear if you are fetching more than UL SDUs here
# is it all messages including acks and DL?
def getNextUlSduPointer(filename):
   try:
      cfg = file(filename,'r')
      # The REST interface will return all SDUs AFTER this SDU ID, if you put it in query
      start_sdu_id = cfg.readline() # (naming) as of 2/15/2016 this is actually the last one you received
      cfg.close()
      return start_sdu_id
   except:
      # If you get this error, you should create an empty file (ex. nextUlSdu.cfg)
      print "ERROR: can't open file: %s to read next Ul SDU pointer" % (filename)
      print "If you get this error, you should create an empty file (ex. nextUlSdu.cfg)"
      print sys.exc_info()[0]
   
#------------------------------------------------------------------------------
# Writes the last message ID to a file, so next query will get all SDUs afterward.
# This function gets imported by other modules
#------------------------------------------------------------------------------
def incrementNextUlSduPointer(filename, last_sdu_id):
   try:
      cfg = file(filename,'w')
      res = cfg.write(last_sdu_id)
      cfg.close()
   except:
      print "ERROR: can't open file: %s to write next Ul SDU pointer" % (filename)
      print sys.exc_info()[0]

#------------------------------------------------------------------------------
# MAIN
#------------------------------------------------------------------------------
rest_conn = httplib.HTTPSConnection(host) # external appliance or hosted network use HTTPSConn
print "rest_conn, host = ", rest_conn, host

def getNextUlSdu(filename):
   start_sdu_id = getNextUlSduPointer(filename)
   (status, last_sdu_id, size, sdus) = pullUlSdu(start_sdu_id)
   if status == 'OK':
      return ('OK', last_sdu_id, size, sdus)
   elif status == 'ERROR':
      return ('ERROR', '','','') # dummy so same fields get returned

if __name__ == '__main__':
   (status, last_sdu_id, size, sdus) = getNextUlSdu('nextUlSdu.cfg')
   print "size = ", size 
   print "sdus  = ", sdus 
   print "last_sdu_id = ", last_sdu_id
