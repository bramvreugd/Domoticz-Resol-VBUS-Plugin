# Domoticz-Resol-VBUS-Plugin
Resol VBUS plugin for Domoticz

## Prerequisites
* Setup and run resul-vbus library (https://github.com/danielwippermann/resol-vbus).
* Start  the "json-live-data-server" example
* Make sure that your Domoticz supports Python plugins (https://www.domoticz.com/wiki/Using_Python_plugins)
* Make sure http://127.0.0.1:3333/api/v1/live-data/ return a list of values in your browser 

## Installation

1. Clone repository into your domoticz plugins folder
```
cd domoticz/plugins
git clone https://github.com/bramvreugd/resol-vbus-domoticz-plugin.git resol-vbus
```
2. Restart domoticz
3. Make sure that "Accept new Hardware Devices" is enabled in Domoticz settings
4. Go to "Hardware" page and add new item with type "resol vbus"
5. Set your ip address of the server where the "json-live-data-server" is runing. Normally localhost 127.0.0.1

Once plugin receive device list from resol-vbus library it will create appropriate domoticz devices. You will find these devices on Setup -> Devices page.

## Plugin update
1. Go to plugin folder and pull new version
```
cd domoticz/plugins/resol-vbus
git pull
```
2. Restart domoticz


Version 1.1 you may need to remove device "volume in total" or change it's type from 243 to 113 and subtype from 28 to 0
