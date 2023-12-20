# Tesla plugin for Domoticz
This plugin integrates the [TeslaPy](https://github.com/tdorssers/TeslaPy) library into a Domoticz plugin.

This plugin is (at this moment) only tested with a 2023 Model Y. I assume other vehicles will work too. The library supports all Tesla products, but this plugin is (for now) only implementing vehicles.

## Installation

### Prerequisites
The following steps need to be taken before plugin installation (generic for any plugin)
1. Python version 3.9 or higher required & Domoticz version 2022.1 (due to extended plugin framework) or greater. 
2. follow the Domoticz guide on [Using Python Plugins](https://www.domoticz.com/wiki/Using_Python_plugins).
3. install the required libraries:
```
sudo apt-get update
sudo apt-get install python3 libpython3-dev libpython3.7-dev
sudo apt-get install python3-requests
sudo python3 -m pip install TeslaPy
```
### install the plugin
1. Go in your Domoticz directory using a command line and open the plugins directory:
 ```cd domoticz/plugins```
2. clone the plugin:
 ```git clone https://github.com/JanJaapKo/TeslaDomoticz```
3. Restart Domoticz:
 ```sudo systemctl restart domoticz```
4. run tesla_prepare to authenticate. Edit the file to hold the email adress registered to your Tesla account, and then:
 ```cd TeslaDomoticz
 python3 tesla_prepare```
 Follow instructions on the command line. Authentication is sussefull when it reports the name of your vehicle
 5. Add the plugin to Domoticz on the hardware page y providing the required configuration attributes
 