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
<plugin key="TeslaDomoticz" name="Tesla for Domoticz plugin" author="Jan-Jaap Kostelijk" version="0.7.0">
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
        <h3>Battery</h3>
        If you poll the car all the time when  not charging, your battery will be drained.
        There is no way for the plugin to determine if you start driving or charging other than polling the car. To save draining and yet to enable polling this mechanism is implemented:
        <ul style="list-style-type:square">
            <li>Forced poll interval - Polls the car actively every x minutes, slightly randomized. Recommended 60 (1 hour). You might want to change it to 999 (once a week approx.).</li>
        </ul>
        The active car polling stops when you are no longer driving or charging is not set.
        <br/>
    </description>
    <params>
        <param field="Username" label="Email-address"           width="200px" required="true"  default="john.doe@gmail.com" >
            <description>Email adress for your Tesla account</description>
        </param>
        <param field="Mode1"    label="ABRP token"              width="300px" required="false" default="1234ab56-7cde-890f-a12b-3cde45678901"/>
	    <param field="Mode3"    label="Intervals (minutes)" width="100px"  required="true" default="60;30;30">
            <description>Polling intervals: supply 3 values (separated by ';'): normal update; charging update; driving update</description>
        </param>
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
import TeslaVehicle

class TeslaPlugin:

    def onStart(self):
        self.log_filename = "tesla_"+Parameters["Name"]+".log"
        Domoticz.Log('Plugin starting')
        if Parameters["Mode6"] == "1":
            Domoticz.Debugging(2)
            #DumpConfigToLog()
            Domoticz.Log('Debug mode')
            logging.basicConfig(format='%(asctime)s - %(levelname)-8s - %(filename)-18s - %(message)s', filename=self.log_filename,level=logging.DEBUG)
        else:
            if Parameters["Mode6"] == "2": logging.basicConfig(format='%(asctime)s - %(levelname)-8s - %(filename)-18s - %(message)s', filename=self.log_filename, level=logging.INFO)
            elif Parameters["Mode6"] == "3": logging.basicConfig(format='%(asctime)s - %(levelname)-8s - %(filename)-18s - %(message)s', filename=self.log_filename, level=logging.WARNING)
            else: logging.basicConfig(format='%(asctime)s - %(levelname)-8s - %(filename)-18s - %(message)-8s', filename=self.log_filename, level=logging.ERROR)

        logging.info("starting plugin version "+Parameters["Version"])

        self.lastHeartbeatTime = 0
        self.runCounter = 5

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
            Domoticz.Debug("Adding maps icon")
            
        if Parameters["Mode6"] == "1":
            #Domoticz.Debugging(1)
            DumpConfigToLog()

        #check upgrading of version needs actions
        self.version = Parameters["Version"]
        self.enabled = self.checkVersion(self.version)
        if not self.enabled:
            return False

        self.p_email = Parameters["Username"]
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
        self.forcepollinterval = float(intervals[0]) * 60
        self.charginginterval = float(intervals[1]) * 60
        self.heartbeatinterval = float(intervals[2])
        if self.heartbeatinterval == "":
            self.heartbeatinterval = float(120)
        else:
            self.heartbeatinterval = float(self.heartbeatinterval) * 60
        
        TeslaServer = TeslaDevice.TeslaServer(self.p_email)
        
        initsuccess = TeslaServer.initialize()
        if initsuccess:
            logging.info("Initialisation succeeded")
        else:
            Domoticz.Error("Initialisation failed, run tesla_prepare first")
            logging.error("Initialisation failed, run tesla_prepare first")
            return False

        self.vehicle_list = TeslaServer.get_devices()
        self.vehicle_dict = {}
        logging.info("Found " + str(len(self.vehicle_list)) + " vehicles")
        logging.debug("list of vehicles from server: " + str(self.vehicle_list))
        for vehicle in self.vehicle_list:
            self.vehicle_dict[vehicle['vin']] = TeslaVehicle.teslaVehicle(vehicle)
            self.vehicle_dict[vehicle['vin']].vehicle.sync_wake_up()
            self.createVehicleDevices(self.vehicle_dict[vehicle['vin']])
            self.updateDevices(self.vehicle_dict[vehicle['vin']])
            logging.info("vehicle " + self.vehicle_dict[vehicle['vin']].car_type + " found, VIN: " + self.vehicle_dict[vehicle['vin']].vin + " called '" + self.vehicle_dict[vehicle['vin']].name + "'")
            logging.info("the vehicle called " + self.vehicle_dict[vehicle['vin']].name + " has charging state " + self.vehicle_dict[vehicle['vin']].charging)

        logging.debug("onStart: vehicle dict: "+str(self.vehicle_dict))
        Domoticz.Log('Plugin starting up done')
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
        self.runCounter = self.runCounter - 1
        if self.runCounter <= 0:
            logging.debug("Polling unit")
            self.runCounter = 10 #check for connection status not every heartbeat         

            #try:
            #manualForcePoll = (Devices[9].nValue == 1)
            manualForcePoll = False
            if manualForcePoll:
                self.lastHeartbeatTime = 0
                UpdateDeviceEx(9, 0, 0)
            for vin, vehicle in self.vehicle_dict.items():
                # at night (between 2259 and 0700) only one in 2 polls is done
                # unless charging or driving
                if 7 <= datetime.now().hour <= 22 or vehicle.is_charging or vehicle.is_driving:
                    heartbeatmultiplier = 1
                else:
                    heartbeatmultiplier = 2
                current_interval = self.forcepollinterval
                if vehicle.is_charging:
                    current_interval = self.charginginterval
                if vehicle.is_driving:
                    current_interval = self.charginginterval
                if vehicle.battery_level <10 and not vehicle.is_charging:
                    # at low battery level, reduce polling to 5 hrs interval
                    current_interval = 5*3600 
                logging.debug("onHeartbeat: vehicle.lastHeartbeatTime = " + str(self.lastHeartbeatTime) + " with seconds interval = " + str(heartbeatmultiplier * current_interval))
                logging.debug("onHeartbeat: vehicle.lastpollTime = " + vehicle.last_poll_time.strftime("%Y-%m-%d %H:%M:%S") )
                #check per vehicle in the list if it needs to be polled
                if self.lastHeartbeatTime == 0 or float((datetime.now() - vehicle.last_poll_time).total_seconds()) > (random.uniform(0.75,1.5)*(heartbeatmultiplier * current_interval)):
                    logging.info(" Updating vehicle " + vehicle.car_type + " VIN: " + vehicle.vin + " called '" + vehicle.name + "'")
                    self.lastHeartbeatTime = datetime.now()
                    try:
                        vehicle.vehicle.sync_wake_up()
                    except ConnectionResetError:
                        logging.error("connection error during vehicle sync")
                        Domoticz.Error("connection error during vehicle sync")
                        return
                    self.updateDevices(vehicle)
        return

    def onDisconnect(self, Connection):
        Domoticz.Log("Device has disconnected")
        return

    def onStop(self):
        logging.info("stopping plugin")
        Domoticz.Log("onStop called")
        return True

    def createVehicleDevices(self, device):
        deviceId = device.vin
        deviceName = device.name
        
        if deviceId not in Devices or (1 not in Devices[deviceId].Units):
            Domoticz.Unit(Unit=1, Type=113, Subtype=0 , Switchtype=3 , Name = deviceName + " - odometer", DeviceID=deviceId).Create()
        if (2 not in Devices[deviceId].Units):
            Domoticz.Unit(Unit=2, Type=243, Subtype=31, Switchtype=0 , Name = deviceName + " - range", DeviceID=deviceId).Create()
        if (3 not in Devices[deviceId].Units):
            Domoticz.Unit(Unit=3, Type=244, Subtype=73, Switchtype=0 , Name = deviceName + " - charging", DeviceID=deviceId).Create()
        if (4 not in Devices[deviceId].Units):
            Domoticz.Unit(Unit=4, TypeName="Percentage", Name = deviceName + " - Battery percentage ", Used=1, DeviceID=deviceId).Create()
        if (5 not in Devices[deviceId].Units):
            Domoticz.Unit(Unit=5, Type=243, Subtype=31, Name = deviceName + " - Remaining charge time",  Options = {'Custom':'1;hrs'}, DeviceID=deviceId).Create()
        if (8 not in Devices[deviceId].Units) and "Maps icon" in Images:
            Domoticz.Unit(Unit=8, Type=243, Subtype=19, Image=Images["Maps icon"].ID, Name="Location update needed", DeviceID=deviceId).Create()
            Devices[deviceId].Units[8].sValue = "Location update needed"
            Devices[deviceId].Units[8].Update()
        if (13 not in Devices[deviceId].Units):
            Domoticz.Unit(Unit=13, Type=243, Subtype=31, Name= deviceName + " - current speed", DeviceID=deviceId).Create()


        '''
            Domoticz.Unit(Name="Inverter temperature (SN: " + deviceId + ")", DeviceID=deviceId,
                            Unit=(self.inverterTemperatureUnit), Type=80, Subtype=5).Create()

        if (5 not in Devices):
            Domoticz.Device(Unit=5, TypeName="Percentage"              , Name="Battery 12v").Create()
        if (6 not in Devices):
            Domoticz.Device(Unit=6, Type=243, Subtype=31, Switchtype=0 , Name="status 12v").Create()
        if (7 not in Devices):
            Domoticz.Device(Unit=7, Type=244, Subtype=73, Switchtype=11, Name="tailgate").Create()
        if (9 not in Devices):
            Domoticz.Device(Unit=9, Type=244, Subtype=73, Switchtype=0 , Name="force status update").Create()
        if (10 not in Devices):
            Domoticz.Device(Unit=10, Type=244, Subtype=73, Switchtype=19 , Name="doors").Create()
        if (11 not in Devices):
            Domoticz.Device(Unit=11, Type=242, Subtype=1,                  Name="airco: off").Create()
        if (12 not in Devices):
            Domoticz.Device(Unit=12, Type=244, Subtype=73, Switchtype=11, Name="hood").Create()
        '''
        logging.info("Devices created.")
        return True
    
    def updateDevices(self,vehicle):
        vehicle.get_vehicle_data()
        deviceId = vehicle.vin
        deviceName = vehicle.name
        if vehicle.odometer is not False:
            UpdateDeviceEx(deviceId, 1, vehicle.odometer, "{:.0f}".format(vehicle.odometer))  # odometer
        if vehicle.battery_range is not False:
            UpdateDeviceEx(deviceId, 2, vehicle.battery_range, "{:.1f}".format(vehicle.battery_range))  # range
        UpdateDeviceEx(deviceId, 3, 0, str(vehicle.is_charging))  # charging
        if vehicle.battery_level is not False and vehicle.battery_level>0:    #avoid to set soc=0% 
            UpdateDeviceEx(deviceId, 4, vehicle.battery_level, str(vehicle.battery_level))  # soc

        if 8 in Devices[deviceId].Units and vehicle.get_google_url is not False:
            location_url = '<a target="_blank" rel="noopener noreferrer" ' + vehicle.get_google_url + deviceName + " - location</a> "
            UpdateDeviceEx(deviceId, 8, 0, location_url)  # location
        else:
            logging.info("no location data in vehicle data found") 
        
        UpdateDeviceEx(deviceId, 13, 0, str(vehicle.speed))  # current speed

        logging.info("Devices updated.")
        return True

    def updateTo1(self):
        """routine to check if we can update to version 1"""
        if len(Devices)>0:
            Domoticz.Error("Devices are present. Please upgrade them before upgrading to this version!")
            Domoticz.Error("Plugin will now exit but will be enabled on next start")
            self._setVersion("1","0","0")
            return False
        else:
            return True

    def checkVersion(self, version):
        """checks actual version against stored version as 'Ma.Mi.Pa' and checks if updates needed"""
        #read version from stored configuration
        ConfVersion = getConfigItem("plugin version", "0.0.0")
        Domoticz.Log("Starting version: " + version )
        logging.info("Starting version: " + version )
        MaCurrent,MiCurrent,PaCurrent = version.split('.')
        MaConf,MiConf,PaConf = ConfVersion.split('.')
        logging.debug("checking versions: current '{0}', config '{1}'".format(version, ConfVersion))
        can_continue = True
        if int(MaConf) < int(MaCurrent):
            Domoticz.Log("Major version upgrade: {0} -> {1}".format(MaConf,MaCurrent))
            logging.info("Major version upgrade: {0} -> {1}".format(MaConf,MaCurrent))
            #add code to perform MAJOR upgrades
            if int(MaConf) < 1:
                can_continue = self.updateTo1()
        elif int(MiConf) < int(MiCurrent):
            Domoticz.Debug("Minor version upgrade: {0} -> {1}".format(MiConf,MiCurrent))
            logging.debug("Minor version upgrade: {0} -> {1}".format(MiConf,MiCurrent))
            #add code to perform MINOR upgrades
        elif int(PaConf) < int(PaCurrent):
            Domoticz.Debug("Patch version upgrade: {0} -> {1}".format(PaConf,PaCurrent))
            logging.debug("Patch version upgrade: {0} -> {1}".format(PaConf,PaCurrent))
            #add code to perform PATCH upgrades, if any
        if ConfVersion != version and can_continue:
            #store new version info
            self._setVersion(MaCurrent,MiCurrent,PaCurrent)
        return can_continue

    def _setVersion(self, major, minor, patch):
        #set configs
        logging.debug("Setting version to {0}.{1}.{2}".format(major, minor, patch))
        setConfigItem(Key="MajorVersion", Value=major)
        setConfigItem(Key="MinorVersion", Value=minor)
        setConfigItem(Key="patchVersion", Value=patch)
        setConfigItem(Key="plugin version", Value="{0}.{1}.{2}".format(major, minor, patch))
        
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
    Domoticz.Debug("Parameters count: " + str(len(Parameters)))
    for x in Parameters:
        if Parameters[x] != "":
            Domoticz.Debug("' - " + x + "':'" + str(Parameters[x]) + "'")
    #Domoticz.Debug("Settings count: " + str(len(Settings)))
    #for x in Settings:
    #    Domoticz.Debug("'" + x + "':'" + str(Settings[x]) + "'")
    Domoticz.Debug("Image count: " + str(len(Images)))
    for x in Images:
        Domoticz.Debug("' - " + x + "':'" + str(Images[x]) + "'")
    Domoticz.Debug("Device count: " + str(len(Devices)))
    for DeviceName in Devices:
        Device = Devices[DeviceName]
        Domoticz.Debug("Device:       '" + str(Device) + "'")
        for UnitNo in Device.Units:
            Unit = Device.Units[UnitNo]
            Domoticz.Debug(" - Unit:       '" + str(Unit) + "'")
    Configurations = Domoticz.Configuration()
    Domoticz.Debug("Configurations count: " + str(len(Configurations)))
    for x in Configurations:
        if Configurations[x] != "":
            Domoticz.Debug( " - Configuration '" + x + "':'" + str(Configurations[x]) + "'")

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
    if (Device in Devices and Unit in Devices[Device].Units):
        if (Devices[Device].Units[Unit].nValue != nValue) or (Devices[Device].Units[Unit].sValue != sValue) or AlwaysUpdate:
                logging.info("Updating device '"+Devices[Device].Units[Unit].Name+ "' with current sValue '"+Devices[Device].Units[Unit].sValue+"' to '" +sValue+"'")
            #try:
                Devices[Device].Units[Unit].nValue = nValue
                Devices[Device].Units[Unit].sValue = sValue
                Devices[Device].Units[Unit].Update()
                
                #logging.debug("Update "+str(nValue)+":'"+str(sValue)+"' ("+Devices[Device].Units[Unit].Name+")")
            # except:
                # Domoticz.Error("Update of device failed: "+str(Unit)+"!")
                # logging.error("Update of device failed: "+str(Unit)+"!")
    else:
        Domoticz.Error("trying to update a non-existent unit "+str(Unit)+" from device "+str(Device))
        logging.error("trying to update a non-existent unit "+str(Unit)+" from device "+str(Device))
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
