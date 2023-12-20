#           Tesla Domoticz Plugin
#
# Copyright 2023 Jan-Jaap Kostelijk
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is furnished
# to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN
# AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
"""
<plugin key="TeslaDomoticz" name="Tesla for Domoticz plugin" author="Jan-Jaap Kostelijk" version="0.2.0">
    <description>
        <h2>Tesla Domoticz plugin</h2>
        A plugin for Tesla EV's . Use at own risk!
        <br/>
        This plugin will communicate with servers of Tesla and through them with your car.
        <br/>
        Polling your car means draining the battery and worst case, an empty battery.
        <br/><br/>
        <h3>ABRP (optional) </h3>
        This plugin will send current state of charge (SoC) and local temperature to your ABRP account to have the most accurate route planning, even on the road. <br/>
        Your ABRP token can be found here: Settings - Car model, 
	Click on settings next to you car, 
	click on settings (arrow down) on the page of your car. 
	Scroll down a bit and click on Show live data instructions and next on the blue "Link Torque"-box.
        Click Next, Next, Next and see: "Set User Email Address to the following token". Click on the blue "Copy" box next to the token.
        <br/>
        If you omit your ABRP token, then no information will be sent to ABRP.
        <br/>
        <h3>12V auxiliary battery</h3>
        If you poll the car all the time, when not driving or not charging, your 12V battery may be drained, depending on the settings of your car to charge the auxiliary battery.
        There is no way for the plugin to determine if you start driving or charging other than polling the car. To save draining and yet to enable polling this mechanism is implemented:
        <ul style="list-style-type:square">
            <li>Forced poll interval - Polls the car actively every x minutes, slightly randomized. Recommended 60 (1 hour). You might want to change it to 999 (once a week approx.).</li>
        </ul>
        The active car polling stops when you are no longer driving or charging is not set.
        <br/>
    </description>
    <params>
        <param field="Username" label="Email-address"           width="200px" required="true"  default="john.doe@gmail.com"                  />
        <param field="Password" label="Password"                width="200px" required="true"  default="myLittleSecret" password="true"      />
        <param field="Mode1"    label="ABRP token"              width="300px" required="false" default="1234ab56-7cde-890f-a12b-3cde45678901"/>
	    <param field="Mode3"    label="Intervals (in minutes: force; charging; heartbeat)" width="100px"  required="true" default="60;30;10"                  />
        <param field="Mode6" label="Log level" width="75px">
            <options>
                <option label="1. Debug" value="1"/>
                <option label="2. Info" value="2"/>
                <option label="3. Warning" value="3"/>
                <option label="4. Error" value="4" default = "true"/>
                <option label="5. Critical" value="5"/>
            </options>
        </param>
    </params>
</plugin>
"""

try:
    import DomoticzEx as Domoticz
except ImportError:
    #import fake domoticz modules and setup fake domoticz instance to enable unit testing
    from fakeDomoticz import *
    from fakeDomoticz import Domoticz
    Domoticz = Domoticz()
import logging
import random
from datetime import datetime
import TeslaDevice

class TeslaPlugin:

    def onStart(self):
        self.log_filename = "tesla_"+Parameters["Name"]+".log"
        if Parameters["Mode6"] == "1":
            Domoticz.Debugging(2)
            DumpConfigToLog()
            Domoticz.Log('Debug mode')
            logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', filename=self.log_filename,level=logging.DEBUG)
        else:
            if Parameters["Mode6"] == "2": logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', filename=self.log_filename, level=logging.INFO)
            elif Parameters["Mode6"] == "3": logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', filename=self.log_filename, level=logging.WARNING)
            else: logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', filename=self.log_filename, level=logging.ERROR)

        logging.info("starting plugin version "+Parameters["Version"])
        '''
        # add custom images
        CLOSED_ICON = "Closed"
        CHARGING_ICON = "Charging"
        AFSTAND_ICON = "Distance"
        # Dry Logo
        if self.CLOSED_ICON in Images:  Domoticz.Debug("ID: " + str(Images[self.CLOSED_ICON].ID))
        else:                           Domoticz.Image(CLOSED_ICON+".zip").Create()
        if self.CHARGING_ICON in Images:Domoticz.Debug("ID: " + str(Images[self.CHARGING_ICON].ID))
        else:                           Domoticz.Image(CHARGING_ICON+".zip").Create()
        if self.AFSTAND_ICON in Images: Domoticz.Debug("ID: " + str(Images[self.AFSTAND_ICON].ID))
        else:                           Domoticz.Image(AFSTAND_ICON+".zip").Create()
        '''
        if "Maps icon" not in Images:
            Domoticz.Image("Maps icon.zip").Create()
            
        if Parameters["Mode6"] == "1":
            Domoticz.Debugging(1)
            DumpConfigToLog()
        self.p_email = Parameters["Username"]
        #self.p_password = Parameters["Password"] # TODO: check if not needed elsewhere
        self.p_abrp_token = Parameters["Mode1"]
        #self.p_abrp_carmodel = Parameters["Mode2"] # TODO"filter this info from Tesla API
        self.p_homelocation = Settings["Location"]
        if self.p_homelocation is None:
            Domoticz.Log("Unable to parse coordinates")
            self.p_homelocation = "52.0930241;4.3423724,17"
            return False
        intervals = Parameters["Mode3"]
        for delim in ',;:': intervals = intervals.replace(delim, ' ')
        intervals=intervals.split(" ")
        self.p_forcepollinterval = float(intervals[0])
        self.p_charginginterval = float(intervals[1])
        self.p_heartbeatinterval = float(intervals[2])
        
        TeslaServer = TeslaDevice.TeslaAnyDevice(self.p_email)
        
        initsuccess = TeslaServer.initialize()
        if initsuccess:
                logging.info("Initialisation succeeded")
        else:
                Domoticz.Error("Initialisation failed, run tesla_prepare first")
                logging.error("Initialisation failed, run tesla_prepare first")
                return False
        return True


    def onConnect(self, Connection, Status, Description):
        return True

    def onMessage(self, Connection, Data):
        return True

    def onCommand(self, Device, Unit, Command, Level, Color):
        logging.info("devcie %s, unit %s, Command %s Level %s Color %s",Device, Unit, Command, Level, Color)
        return True

    def onNotification(self, Name, Subject, Text, Status, Priority, Sound, ImageFile):
        return True

    def onHeartbeat(self):
        return
        try:
            manualForcePoll = (Devices[9].nValue == 1)
            if manualForcePoll:
                lastHeartbeatTime = 0
                UpdateDevice(9, 0, 0)
            # at night (between 2300 and 700) only one in 2 polls is done
            heartbeatmultiplier = (1 if 7 <= datetime.now().hour <= 22 else 2)
            if lastHeartbeatTime == 0 or float((datetime.now() - lastHeartbeatTime).total_seconds()) > (random.uniform(0.75,1.5)*(heartbeatmultiplier * heartbeatinterval)):
                lastHeartbeatTime = datetime.now()
                updated, parsedStatus, afstand, googlelocation = pollcar(manualForcePoll)
                pluginName = Devices[11].Name.split("-")[0]
                googlelocation = '<a target="_blank" rel="noopener noreferrer" ' + googlelocation + pluginName + " - location</a> "
                if updated:
                    logging.debug("about to update devices")
                    logging.debug("parsedStatus: " + str(parsedStatus))
                    UpdateDevice(1, 0, parsedStatus['odometer'])  # kmstand
                    UpdateDevice(2, 0, parsedStatus['range'])  # range
                    UpdateDevice(3, parsedStatus['charging'], parsedStatus['charging'])  # charging
                    if (parsedStatus['chargeHV']>0):    #avoid to set soc=0% 
                        UpdateDevice(4, parsedStatus['chargeHV'], parsedStatus['chargeHV'])  # soc
                    UpdateDevice(5, parsedStatus['charge12V'], parsedStatus['charge12V'])  # soc12v
                    UpdateDevice(6, parsedStatus['status12V'], parsedStatus['status12V'])  # status 12v
                    UpdateDevice(7, parsedStatus['trunkopen'], parsedStatus['trunkopen'])  # tailgate
                    UpdateDevice(12, parsedStatus['hoodopen'], parsedStatus['hoodopen'])  # hood
                    UpdateDevice(13, 0, str(parsedStatus['speed'])+" km/h")  # current speed
                    UpdateDevice(14, 0, str(parsedStatus['chargingTime']/60))  # remaining charge time in hrs
                    if Devices[8].Name != str(afstand) or str(Devices[8].sValue) != googlelocation:
                        Devices[8].Update(nValue=0, sValue=googlelocation, Name=pluginName + "- Distance from home: " + str(afstand))
                        Domoticz.Log("Update " +  str(afstand) + "' (" + Devices[8].Name + ")")
                    UpdateDevice(10, parsedStatus['locked'], parsedStatus['locked'])  # deuren
                    pluginName = Devices[11].Name.split(":")[0]
                    climate = pluginName + ": on" if (parsedStatus['climateactive'] == True) else pluginName + ": off"
                    Level = parsedStatus['temperature']
                    Devices[11].Update(nValue=0, sValue=str(Level), Name= climate)
        except:
            logging.debug("heartbeat wasnt set yet")
        return

    def onDisconnect(self, Connection):
        Domoticz.Log("Device has disconnected")
        return

    def onStop(self):
        Domoticz.Log("onStop called")
        return True


    def createVehicleDevices(self, deviceId):
        if (4 not in Devices):
            Domoticz.Unit(Unit=4, TypeName="Percentage", Name="Battery percentage" + str(deviceId), DeviceID=deviceId).Create()

            Domoticz.Unit(Name="Inverter temperature (SN: " + serialNumber + ")", DeviceID=serialNumber,
                            Unit=(self.inverterTemperatureUnit), Type=80, Subtype=5).Create()

        '''
        if (1 not in Devices):
            Domoticz.Device(Unit=1, Type=113, Subtype=0 , Switchtype=3 , Name="odometer").Create()
        if (2 not in Devices):
            Domoticz.Device(Unit=2, Type=243, Subtype=31, Switchtype=0 , Name="range").Create()
        if (3 not in Devices):
            Domoticz.Device(Unit=3, Type=244, Subtype=73, Switchtype=0 , Name="charging").Create()
        if (5 not in Devices):
            Domoticz.Device(Unit=5, TypeName="Percentage"              , Name="Battery 12v").Create()
        if (6 not in Devices):
            Domoticz.Device(Unit=6, Type=243, Subtype=31, Switchtype=0 , Name="status 12v").Create()
        if (7 not in Devices):
            Domoticz.Device(Unit=7, Type=244, Subtype=73, Switchtype=11, Name="tailgate").Create()
        if (8 not in Devices):
            Domoticz.Device(Unit=8, Type=243, Subtype=19, Image=Images["Maps icon"].ID, Name="distance from home: 0").Create()
            Devices[8].Update(nValue=0, sValue="Location update needed")
        if (9 not in Devices):
            Domoticz.Device(Unit=9, Type=244, Subtype=73, Switchtype=0 , Name="force status update").Create()
        if (10 not in Devices):
            Domoticz.Device(Unit=10, Type=244, Subtype=73, Switchtype=19 , Name="doors").Create()
        if (11 not in Devices):
            Domoticz.Device(Unit=11, Type=242, Subtype=1,                  Name="airco: off").Create()
        if (12 not in Devices):
            Domoticz.Device(Unit=12, Type=244, Subtype=73, Switchtype=11, Name="hood").Create()
        if (13 not in Devices):
            Domoticz.Device(Unit=13, Type=243, Subtype=31, Name="current speed").Create()
        if (14 not in Devices):
            Domoticz.Device(Unit=14, Type=243, Subtype=31, Name="Remaining charge time",  Options = {'Custom':'1;hrs'}).Create()
        '''
        logging.info("Devices created.")
        return True
    
global _plugin
_plugin = TeslaPlugin()

def onStart():
    global _plugin
    _plugin.onStart()

def onStop():
    global _plugin
    _plugin.onStop()

def onConnect(Connection, Status, Description):
    global _plugin
    _plugin.onConnect(Connection, Status, Description)

def onMessage(Connection, Data):
    global _plugin
    _plugin.onMessage(Connection, Data)

def onCommand(Device, Unit, Command, Level, Color):
    global _plugin
    _plugin.onCommand(Device, Unit, Command, Level, Color)

def onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile):
    global _plugin
    _plugin.onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile)

def onDisconnect(Connection):
    global _plugin
    _plugin.onDisconnect(Connection)

def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()

# Generic helper functions
def DumpConfigToLog():
    for x in Parameters:
        if Parameters[x] != "":
            Domoticz.Debug("'" + x + "':'" + str(Parameters[x]) + "'")
    #Domoticz.Debug("Settings count: " + str(len(Settings)))
    #for x in Settings:
    #    Domoticz.Debug("'" + x + "':'" + str(Settings[x]) + "'")
    Domoticz.Debug("Image count: " + str(len(Images)))
    for x in Images:
        Domoticz.Debug("'" + x + "':'" + str(Images[x]) + "'")
    Domoticz.Debug("Device count: " + str(len(Devices)))
    for DeviceName in Devices:
        Device = Devices[DeviceName]
        Domoticz.Debug("Device:       '" + str(Device) + "'")
        for UnitNo in Device.Units:
            Unit = Device.Units[UnitNo]
            Domoticz.Debug(" - Unit:       '" + str(Unit) + "'")
    return

def UpdateDevice(Unit, nValue, sValue):
    # Make sure that the Domoticz device still exists (they can be deleted) before updating it
    if (Unit in Devices):
        if (Devices[Unit].nValue != nValue) or (str(Devices[Unit].sValue) != str(sValue)):
            Devices[Unit].Update(nValue=nValue, sValue=str(sValue))
            Domoticz.Log("Update " + str(nValue) + ":'" + str(sValue) + "' (" + Devices[Unit].Name + ")")
    return

def UpdateDeviceEx(Device, Unit, nValue, sValue, AlwaysUpdate=False):
    # Make sure that the Domoticz device still exists (they can be deleted) before updating it
    if (Device in Devices):
        logging.debug("Updating device '"+Devices[Device].Units[Unit].Name+ "' with current sValue '"+Devices[Device].Units[Unit].sValue+"' to '" +sValue+"'")
        if (Devices[Device].Units[Unit].nValue != nValue) or (Devices[Device].Units[Unit].sValue != sValue) or AlwaysUpdate:
            #try:
                Devices[Device].Units[Unit].nValue = nValue
                Devices[Device].Units[Unit].sValue = sValue
                Devices[Device].Units[Unit].Update()
                
                logging.debug("Update "+str(nValue)+":'"+str(sValue)+"' ("+Devices[Device].Units[Unit].Name+")")
            # except:
                # Domoticz.Error("Update of device failed: "+str(Unit)+"!")
                # logging.error("Update of device failed: "+str(Unit)+"!")
    return


# Configuration Helpers
def getConfigItem(Key=None, Default={}):
   Value = Default
   try:
       Config = Domoticz.Configuration()
       if (Key != None):
           Value = Config[Key] # only return requested key if there was one
       else:
           Value = Config      # return the whole configuration if no key
   except KeyError:
       Value = Default
   except Exception as inst:
       Domoticz.Error("Domoticz.Configuration read failed: '"+str(inst)+"'")
   return Value
   
def setConfigItem(Key=None, Value=None):
    Config = {}
    if type(Value) not in (str, int, float, bool, bytes, bytearray, list, dict):
        Domoticz.Error("A value is specified of a not allowed type: '" + str(type(Value)) + "'")
        return Config
    try:
       Config = Domoticz.Configuration()
       if (Key != None):
           Config[Key] = Value
       else:
           Config = Value  # set whole configuration if no key specified
       Config = Domoticz.Configuration(Config)
    except Exception as inst:
       Domoticz.Error("Domoticz.Configuration operation failed: '"+str(inst)+"'")
    return Config
