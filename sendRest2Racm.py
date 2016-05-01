#!/bin/env python
# send one DL SDU from REST interface to rACM

# Configure command line parser.  Make global for simplicity of access
global optparse
from optparse import OptionParser
parser = OptionParser(description = 'Send DL REST payload from command line.')
parser.add_option('-n','--nodeId',dest='nodeIdTarget',
  help='Node specified by the hexadecimal node ID (e.g. 0x1d234)')
parser.add_option('-t','--messageTag',dest='messageTag',
  default='11112223-04d3-4a21-a8e4-148130b5484c',
  help='Message tag identifier in UUID format')
parser.add_option('-p','--payloadHex',dest='payloadHex',
  default='0301870010',
  help='Payload as a hexadecimal string (use no 0x prefix).  Default message is to flash LED eight times on rACM')
parser.add_option('-s','--serialString',dest='bSerialString',
  action="store_true", default=False,
  help='Sends payload as an ASCII string.  Must be ASCII printable!')

(options, args) = parser.parse_args()

import sys
import httplib
from getLoginInfo import getLoginInfo
from xml.dom import minidom
from xml.parsers.expat import ExpatError
from sendSerialText2Rest import sendSerialText2Rest

def main():

    options.nodeIdTarget = "0x569d7"
    print "Tag: %s" % options.nodeIdTarget
    #--------------------------------------------------------------------------
    # CONSTANTS and CONFIG:
    #--------------------------------------------------------------------------
    print 'Payload: %s' % options.payloadHex
    print 'Tag ID: %s' % options.messageTag

    # Get REST Login Info from a file
    (host, username, password) = getLoginInfo("login_info.json")
    rest_headers = {"Username": username,
                    "Password": password,
                    "Accept":"application/xml",
                    "Content-Type":"application/xml"}
    body_str =  "<downlink xmlns='http://www.ingenu.com/data/v1/schema'>"
    body_str += "<datagramDownlinkRequest>"
    body_str += "<tag>%s</tag>" % options.messageTag
    body_str += "<nodeId>%s</nodeId>" % options.nodeIdTarget
    body_str += "<payload>%s</payload>" % options.payloadHex
    body_str += "</datagramDownlinkRequest>"
    body_str += "</downlink>"


    rest_conn = httplib.HTTPSConnection(host) # external appliance or hosted network use HTTPSConn

    # If this is for a serial string demo, run this logic and exit.
    if options.bSerialString:
        sendSerialText2Rest(options.payloadHex, options.nodeIdTarget)
        return

    # Note you can append to this url:
    data_url = "/data/v1/send"
    url = data_url
    url = url.replace('\n','').replace('\r','') # make sure no carriage return/line feed
    try:
        rest_conn.request("POST", url, body_str, rest_headers)
        response = rest_conn.getresponse() # sometimes fails with BadStatusLine or CannotSendRequest
        result = response.read()
        print 'http POST response: %s' % result

        # This parsing is not really necessary... Have another console open and
        # monitoring data on the uplink

        #dom = minidom.parseString(result)
        #(last_sdu_id, sdus) = parseResults(dom, sdus)
        #size = len(sdus)
        #return ('OK', last_sdu_id, size, sdus)
    except:
        print 'ERROR(pullUlSdu): ', sys.exc_info()[:2]
        print 'url ', url, 'rest_headers ', rest_headers
        print 'response= ', response # 'This method may not be used.'
        print 'result = ', result
        print 'dom = ', dom
        rest_conn.close() # This line helps with BadStatusLine error recovery
        # added 2 dummy return values at end to match success case
        return ('ERROR', str(sys.exc_info()[0]),'','')

#########################################################################
# Actually run the program:
# (you can start an interactive session and import this file, and this will
# keep main from executing then)
#########################################################################
if __name__ == '__main__':
    sys.exit(main())
