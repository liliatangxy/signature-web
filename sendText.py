import httplib

def sendText(phoneNumber, message):
   host = 'textbelt.com'
   url = '/text'
   headers = {"Content-Type": "application/x-www-form-urlencoded"}
   body = "number=" + phoneNumber + "&message=" + message
   conn = httplib.HTTPConnection(host)
   conn.request("POST", url, body, headers)
   response = conn.getresponse()
   result = response.read()
   return result
