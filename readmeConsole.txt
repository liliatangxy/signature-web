This set of sample python scripts demonstrates how to query the Intellect 1.0 
REST interface for uplink (UL) traffic, as well as provides the capability
to send a unicast message on the downlink (DL). 

Uplink messages are defined as service data unit packets (SDU) in the direction
of the rACM to the Intellect platform.

Downlink messages are defined as SDUs in the direction of the Intellect
platform to the rACM device.

Setup
------
1. Edit the file login_info.json to include the intellect login credentials.
        host     - Intellect server.  Should always be "intellect.ingenu.com"
        username - Username provided by Ingenu, in a string format. 
                   (e.g "kenneth.sinsuan.ingenudemo@ingenu.com")
        password - Password in a string format (e.g. "thisPassword")

2. Edit the file "createDevice.py", using it as a starting template.  Create a 
   python diectionary entry for each device on your demo network.  The fields 
   are:

        desc   - Text description of the device
        nodeId - The RPMA node's MAC address.  This can be found on the node
                 label in the form of "MAC: 00056AA3".  Enter the field in with
                 the "0x" prefix (ex: 0x56a3b)
        parser - Specify the parser to use for the console display.  The parser
                 converts the raw rACM application payload into a human readable
                 format.  The current selection of parsers are as follows...

                 gps_2 - GPS OTA RFDT application.                 
                 intrusion_detector_1 - Intrusion Detection + Internal K20 Temp.
                 intrusion_detector_2 - Variant of "intrusion_detector_1"
                 temperature_humidity_1 - Omega 4-20 mA demo application. 
                 serial_1 - RS232 demo application. 
                 pulse_1 - Default rACM application, which is a pulse counter.

                 If a custom parser needs to be created, see step 2a.

        m2x_device_id - Not used for the console demo.  Leave as an empty string 
                 (ex: '').
        m2x_primary_key - Not used for the console demo.  Leave as an empty 
                 string.  (ex: '').
        alarm_email_enabled - Not used for the console demo.  Leave at 0.
        alarm_email_list - Not used for the console demo.  Leave as empty list 
                 (ex: []) 

2a.  Creation of a custom parser.  This step can be skipped if a default parser
   already exist.  Note that an existing parser may need to be "reconfigured"
   to have the "expectedSensors" configuration match the rACM configuration.

   Step 1:  Copy an existing parser template within the module "parsers.py".  
            A simple parser to start out with is the "parser_pulse_1".  Be 
            sure to give the parser a unique name.

   Step 2:  Configure the following fields in the expectedSensors dictionary.
              
            sensorId - This is maps to the appropriate APP_INTF pin as follows:

                         0 : APP_INTF_1
                         1 : APP_INTF_2
                         2 : APP_INTF_3
                         3 : APP_INTF_4
                         4 : APP_INTF_5 
                         5 : APP_INTF_6 (Fixed usage for ANA_IN0)
                         6 : APP_INTF_7 (Reserved)
                         7 : APP_INTF_8 (Fixed usage for Vbatt Measure)

            sensorType - Sensor interface types.  This defines the format of
                         the sensor data.  See Table 23 of rACM Developer Guide.
                         Some common values are listed below.
                       
                         0x012 : 32-bit unsigned, pulse counts
                         0x050 : 16-bit signed, Temperature, in Fahrenheit 
                         0x051 : 8-bit signed, Temperature, in Celsius  
                         0x090 : 8-bit unsigned, Digital I/O Data
                         0x0B0 : 8-bit unsigned, Humidity [%] 
                         0xFFE : GPS RSSI
                         0xFFF : Serial UART data

            sensorName - Sensor name 
            sensorDesc - Desription of sensor

   Step 3: Configure the dictionay list of "expectedAlarmTypes".  If no alarms
           are required, leave as an empty list.  Otherwise, specify the 
           application interface pin that can generate an alarm

   Step 4: Modify the top level script, "rest2console.py", and add an "else"
           clause for the new parser.  One should reference an existing parser
           in the general "if-else" clause.  A simple example to use as a 
           template is "pulse_1" parser.

   Step 4: It is recommended to add a test stub in the "__main__" function 
           within the parsers.py module.

3. Open a console window ("DOS box" for windows) to monitor the UL SDU traffic.
   Within that console, run the command:  

   python rest2console.py

   One should see a scrolling display of information from the parsing of REST 
   UL data.  The test script tracks the last UL SDU received, so upon first 
   starting the script, one may see a rapidly scrolling display until the  
   test script has "caught up".  This could take several minutes.

4. Open a second, concurrent console window to send DL SDU traffic.  To send a
   downlink, run the following command, choosing the node ID to target (in 
   this example, it is 0x56aae).

   python sendRest2Racm.py -n 0x56aa3.
  
   The default payload toggles the LED for about 8 seconds, alternating between 
   orange and blue blinks.

   The user can also specify a unique payload using the -p option.  The 
   following command sends a command key/value pair to assert a digital
   output (assuming APP_INTF4 has been configured as a digital ouput)

   python sendRest2Racm.py -n 0x1eb9 -p 0x03011c0140

   A tag ID can be specified to help correlate the response messages on the 
   uplink.  This can be done using the '-t' option.  The tag must be in a 
   qualified UUID format.  The console monitoring the UL SDU messages will 
   show an acknowledgement type message with the associated tag ID upon 
   successful transission of the message.
