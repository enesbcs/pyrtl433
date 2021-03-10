Be a patron at [Patreon](https://www.patreon.com/enesbcs)

# PyRTL433 - Domoticz Python Plugin
Python plugin for RTL-SDR receiving through MQTT protocol

MQTT parts based on heavily on the [zigbee2mqtt] project (https://github.com/stas-demydiuk/domoticz-zigbee2mqtt-plugin) 
big thanks for it!

## Prerequisites

Tested and works with Domoticz v4.x.

If you do not have a working Python >=3.5 installation, please install it first! ( https://www.domoticz.com/wiki/Using_Python_plugins )

Setup and run MQTT broker and an rtl_433 as:
rtl_433 -F "mqtt://MQTTSERVERIP:1883,retain=0"

## Installation

1. Clone repository into your domoticz plugins folder
```
cd domoticz/plugins
git clone https://github.com/enesbcs/pyrtl433.git
```
2. Restart domoticz
3. Go to "Hardware" page and add new item with type "PyRTL433"
4. Set your MQTT server address and port to plugin settings
5. Remember to allow new devices discovery in Domoticz settings and in plugin settings

Once plugin receive any MQTT message from RTLSDR it will try to create appropriate device.

## Plugin update

1. Stop domoticz
2. Go to plugin folder and pull new version
```
cd domoticz/plugins/pyrtl433
git pull
```
3. Start domoticz

