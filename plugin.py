"""
<plugin key="PyRtl433" name="PyRtl433 RTL-SDR MQTT receiver" version="0.1.0">
    <description>
      Simple plugin to interpret MQTT messages coming from RTL_433
      <br/>Please start the command below manually on the machine which has RTLSDR:<br/>
      rtl_433 -F "mqtt://mqttserverip:1883,retain=0"
    </description>
    <params>
        <param field="Address" label="MQTT Server address" width="300px" required="true" default="127.0.0.1"/>
        <param field="Port" label="Port" width="300px" required="true" default="1883"/>
        <param field="Username" label="Username" width="300px"/>
        <param field="Password" label="Password" width="300px" default="" password="true"/>

        <param field="Mode1" label="Topic" width="300px" required="true" default="rtl_433"/>

        <param field="Mode2" label="Enable new device creation" width="75px">
            <options>
                <option label="True" value="1" default="true"/>
                <option label="False" value="0"/>
            </options>
        </param>

        <param field="Mode6" label="Debug" width="75px">
            <options>
                <option label="Verbose" value="Verbose"/>
                <option label="True" value="Debug"/>
                <option label="False" value="Normal" default="true" />
            </options>
        </param>
    </params>
</plugin>
"""
errmsg = ""
try:
 import Domoticz
except Exception as e:
 errmsg += "Domoticz core start error: "+str(e)
try:
 import json
except Exception as e:
 errmsg += " Json import error: "+str(e)
try:
 import time
except Exception as e:
 errmsg += " time import error: "+str(e)
try:
 import re
except Exception as e:
 errmsg += " re import error: "+str(e)
try:
 from mqtt import MqttClient
except Exception as e:
 errmsg += " MQTT client import error: "+str(e)

class BasePlugin:
    mqttClient = None

    def __init__(self):
     return

    def onStart(self):
     global errmsg
     self.devnames = []
     self.devtimes = []
     if errmsg =="":
      try:
        Domoticz.Heartbeat(10)
        self.debugging = Parameters["Mode6"]
        if self.debugging == "Verbose":
            Domoticz.Debugging(2+4+8+16+64)
        if self.debugging == "Debug":
            Domoticz.Debugging(2)
        self.base_topic = Parameters["Mode1"]
        self.learnmode  = Parameters["Mode2"]
        self.mqttserveraddress = Parameters["Address"].strip()
        self.mqttserverport = Parameters["Port"].strip()
        self.mqttClient = MqttClient(self.mqttserveraddress, self.mqttserverport, "", self.onMQTTConnected, self.onMQTTDisconnected, self.onMQTTPublish, self.onMQTTSubscribed)
      except Exception as e:
        Domoticz.Error("MQTT client start error: "+str(e))
        self.mqttClient = None
     else:
        Domoticz.Error("Your Domoticz Python environment is not functional! "+errmsg)
        self.mqttClient = None

    def checkDevices(self):
        Domoticz.Debug("checkDevices called")

    def onStop(self):
        Domoticz.Debug("onStop called")

    def onCommand(self, Unit, Command, Level, Color):  # react to commands arrived from Domoticz
        global Devices
        if self.mqttClient is None:
         return False
        Domoticz.Debug("Command: " + Command + " (" + str(Level) + ") Color:" + Color)
        if Command in ["On","Off"]:
         if Command=="On":
          Devices[Unit].Update(nValue=1,sValue=str(Command))
         else:
          Devices[Unit].Update(nValue=0,sValue=str(Command))

    def onConnect(self, Connection, Status, Description):
       if self.mqttClient is not None:
        self.mqttClient.onConnect(Connection, Status, Description)

    def onDisconnect(self, Connection):
       if self.mqttClient is not None:
        self.mqttClient.onDisconnect(Connection)

    def onMessage(self, Connection, Data):
       if self.mqttClient is not None:
        try:
         self.mqttClient.onMessage(Connection, Data)
        except:
         pass

    def onHeartbeat(self):
      Domoticz.Debug("Heartbeating...")
      if self.mqttClient is not None:
       try:
        # Reconnect if connection has dropped
        if (self.mqttClient._connection is None) or (not self.mqttClient.isConnected):
            Domoticz.Debug("Reconnecting")
            self.mqttClient._open()
        else:
            self.mqttClient.ping()
       except Exception as e:
        Domoticz.Error(str(e))

    def onMQTTConnected(self):
       if self.mqttClient is not None:
        if self.base_topic and self.base_topic != "#":
         topic = self.base_topic + '/#'
        else:
         topic = "rtl_433/#"
#        if "events" not in topic:
#         topic += "/events"
        self.mqttClient.subscribe([topic])

    def onMQTTDisconnected(self):
        Domoticz.Debug("onMQTTDisconnected")

    def onMQTTSubscribed(self):
        Domoticz.Debug("onMQTTSubscribed")

    def onMQTTPublish(self, topic, message): # process incoming MQTT statuses
        try:
         topic = str(topic)
         message2 = str(message)
        except:
         Domoticz.Debug("MQTT message is not a valid string!") #if message is not a real string, drop it
         return False
        try:
         if "'" in message:
          message = message.replace("'",'"') # replace invalid single quotes to double quotes
         jmsg = json.loads(message)
         message = jmsg # reconstruct json struct
        except:
         pass
        mqttpath = topic.split('/')
        if "/events" in topic:
         Domoticz.Debug("MQTT message: " + topic + " " + str(message2))
         data = ""
         if 'rows' in message: # raw data in events - check for Flex encoder output!
          th = []
          for row in message['rows']:
           try:
            if int(row['len'])>4 and str(row['data']).strip()!="":
             th.append(str(row['data']))
           except:
            pass
          mf = 0
          for i in th:
           cf = th.count(i)
           if cf>mf:
            data = i
            mf = cf
         model = ""
         ch = ""
         st = ""
         try:
          if 'model' in message: # model name in events
           model = str(message['model']).replace("-","_")
          if 'channel' in message:
           ch = str(message['channel'])
          if 'subtype' in message:
           st = str(message['subtype'])
          if st=="":
           if 'unit' in message:
            st = str(message['unit'])
          if ch=="" and st=="":
           if 'id' in message:
            st = str(message['id']) # use id only for last resort, as cheap weather stations generates new id on every restart
         except:
          pass
         devname = self.createdevname(model,st,ch,data,"")
         Domoticz.Debug("dname "+devname)
         try:
          if 'time' in message:
           devtime = str(message['time'])
          else:
           devtime = str(time.time())
         except:
          devtime = str(time.time())
         if devname not in self.devnames:
          self.devnames.append(devname)
          self.devtimes.append(devtime)
         else:
          didx = self.devnames.index(devname)
          if didx>0 and didx<len(self.devtimes):
           if self.devtimes[didx]==devtime: # filter duplicated messages
            return False
#         Domoticz.Debug(devtime)
         signal = 12
         if "rssi" in message:
          try:
           rssi = float(message["rssi"])
          except:
           rssi = 0
          if rssi>-0.134:
           signal = 10
          elif rssi<=-7:
           signal = 0
          else:
           signal = 10 - (rssi * -1.34)
         try:
          Domoticz.Debug(str(message["rssi"])+" "+str(message["snr"])+" "+str(message["noise"]))
         except:
          pass

         battery = 255
         if "battery" in message:
          if (str(message["battery"]).lower()=="low") or (str(message["battery"])=="0"):
           battery = 10
          elif (str(message["battery"]).lower()=="ok") or (str(message["battery"])=="100"):
           battery = 100
         if "battery_ok" in message:
          if (str(message["battery_ok"])=="0"):
           battery = 10
          elif (str(message["battery_ok"])=="1"):
           battery = 100

         state = None # check if is it a binary sensor
         if "state" in message or "command" in message:
            state = False
            if "state" in message:
              state = (message["state"]=="ON")
            if "command" in message:
              state = (message["command"]=="On")
         elif data!="":
            if data[:16]=="ffffffffffffffff": # false positive
             return False
            state = True

         if state is not None:
           self.SendSwitch(devname,state,battery,signal)
           return True

         tempc = None
         if "temperature_C" in message:
            tempc = message['temperature_C']
         elif "temperature_F" in message:
            tempc = str((float(message['temperature_F']) - 32) * 5.0/9.0)
         try:
          tempc = float(tempc)
         except:
          tempc = None
         if tempc<-40 or tempc>80:
          tempc = None
          return False # out of range - false positive

         humi = None
         if "humidity" in message:
           if message["humidity"] == "HH":
             humi = 90
           elif message["humidity"] == "LL":
             humi = 10
           else:
            try:
             humi = float(message['humidity'])
            except:
             humi = None
           if humi<0 or humi>100:
            humi = None

         pressure = None
         if "pressure_hPa" in message:
            pressure = message['pressure']

         if (tempc is not None) and (humi is not None) and (pressure is not None):
               self.SendTempHumBaroSensor(devname+"temphumbaro",tempc,humi,pressure,battery,signal)
         elif (tempc is not None) and (humi is not None):
               self.SendTempHumSensor(devname+"-temphum",tempc,humi,battery,signal)
         elif (tempc is not None):
               self.SendTempSensor(devname+"-temp",tempc,battery,signal)
         elif (humi is not None):
               self.SendHumSensor(devname+"-hum",humi,battery,signal)

         rain = None
         if "rain" in message:
            rain = message['rain']
         elif "rain_mm" in message:
            rain = message['rain_mm']
         elif "rainfall_mm" in message:
            rain = message['rainfall_mm']
         raintotal = None
         if "rain_total" in message:
            raintotal = message['rain_total']

         if rain is not None:
               self.SendRainSensor(devname+"-rain",rain,raintotal,battery,signal)

         depth = None
         if "depth_cm" in message:
            depth = message['depth_cm']
         elif "depth" in message:
            depth = message['depth']

         if depth is not None:
               self.SendDistanceSensor(devname+"-depth",depth,battery,signal)

         try:
          windstr = None
          if "windstrength" in message:
            windstr = message['windstrength']
          elif "wind_speed" in message:
            windstr = message['wind_speed']
          elif "average" in message:
            windstr = message['average']
          elif "wind_avg_km_h" in message:
            windstr = float(message['wind_avg_km_h']) * 0.277777778
          elif "wind_avg_m_s" in message:
            windstr = message['wind_avg_m_s']

          winddir = None
          if "winddirection" in message:
            winddir = str(message['winddirection'])
          elif "wind_direction" in message:
            winddir = str(message['wind_direction'])
          elif "direction" in message:
            winddir = str(message['direction'])

          winddirdeg = 0
          if "wind_dir_deg" in message:
            winddirdeg = str(message['wind_dir_deg'])
            if winddir is None or winddir == "":
             winddir = self.getdirection(winddirdeg)

          windgust = None
          if "wind_gust" in message:
            windgust = message['wind_gust']
          elif "gust" in message:
            windgust = message['gust']
          else:
            windgust = "0"
         except Exception as e:
          pass

         if windstr is not None:
             try:
               self.SendWind(devname+"-wind",winddirdeg,winddir,windstr,windgust,tempc,battery,signal)
             except Exception as e:
              Domoticz.Debug(str(e))

         moisture = None
         if "moisture" in message:
            moisture = message['moisture']

         if (moisture is not None):
               self.SendMoisture(devname+"-moist",moisture,battery,signal)

         power = None
         if "power_W" in message:
            power = message['power_W']

         if (power is not None):
               self.SendWattMeter(devname+"-power",watt,battery,signal)

    def getdevID(self,unitname):
          global Devices
          iUnit = -1
          for Device in Devices:
           try:
            if (Devices[Device].DeviceID.strip() == unitname):
             iUnit = Device
             break
           except:
            pass
          return iUnit

    def SendSwitch(self,unitname,state,battery,rssi):
          global Devices
          iUnit = self.getdevID(unitname)
          if iUnit<0 and self.learnmode!=False: # if device does not exists in Domoticz, than create it
            try:
             iUnit = 0
             for x in range(1,256):
              if x not in Devices:
               iUnit=x
               break
             if iUnit==0:
              iUnit=len(Devices)+1
             Domoticz.Device(Name=unitname, Unit=iUnit,TypeName="Switch",Used=0,DeviceID=unitname).Create()
            except Exception as e:
             Domoticz.Debug(str(e))
             return False
          if iUnit>0:
           try:
            if state==False or (str(state).strip().lower() in ["0","off"]):
             scmd = "Off"
             ncmd = 0
            else:
             scmd = "On"
             ncmd = 1
            if battery is None:
             battery = 255
            Devices[iUnit].Update(nValue=ncmd,sValue=scmd,BatteryLevel=int(battery),SignalLevel=int(rssi))
           except Exception as e:
            Domoticz.Debug(str(e))
            return False

    def SendTempHumBaroSensor(self,unitname,temp,hum,press,battery,rssi):
          global Devices
          iUnit = self.getdevID(unitname)
          if iUnit<0 and self.learnmode!=False: # if device does not exists in Domoticz, than create it
            try:
             iUnit = 0
             for x in range(1,256):
              if x not in Devices:
               iUnit=x
               break
             if iUnit==0:
              iUnit=len(Devices)+1
             Domoticz.Device(Name=unitname, Unit=iUnit,Type=84,Subtype=16,Used=0,DeviceID=unitname).Create() # Temp+Hum+Baro
            except Exception as e:
             Domoticz.Debug(str(e))
             return False
          if iUnit>0:
           sval = str(temp) + ";"+ str(hum)+";"+str(self.gethumstatus(hum))+";"+str(press)+";0"
           try:
            if battery is None:
             battery = 255
            Devices[iUnit].Update(nValue=0,sValue=str(sval),BatteryLevel=int(battery),SignalLevel=int(rssi))
           except:
            Domoticz.Debug(str(e))

    def SendTempHumSensor(self,unitname,temp,hum,battery,rssi):
          global Devices
          iUnit = self.getdevID(unitname)
          if iUnit<0 and self.learnmode!=False: # if device does not exists in Domoticz, than create it
            try:
             iUnit = 0
             for x in range(1,256):
              if x not in Devices:
               iUnit=x
               break
             if iUnit==0:
              iUnit=len(Devices)+1
             Domoticz.Device(Name=unitname, Unit=iUnit,TypeName="Temp+Hum",Used=0,DeviceID=unitname).Create() # Temp+Hum
            except Exception as e:
             Domoticz.Debug(str(e))
             return False
          if iUnit>0:
           sval = str(temp) + ";"+ str(hum)+";"+str(self.gethumstatus(hum))
           try:
            if battery is None:
             battery = 255
            Devices[iUnit].Update(nValue=0,sValue=str(sval),BatteryLevel=int(battery),SignalLevel=int(rssi))
           except:
            Domoticz.Debug(str(e))

    def SendTempSensor(self,unitname,temp,battery,rssi):
          global Devices
          iUnit = self.getdevID(unitname)
          if iUnit<0 and self.learnmode!=False: # if device does not exists in Domoticz, than create it
            try:
             iUnit = 0
             for x in range(1,256):
              if x not in Devices:
               iUnit=x
               break
             if iUnit==0:
              iUnit=len(Devices)+1
             Domoticz.Device(Name=unitname, Unit=iUnit,TypeName="Temperature",Used=0,DeviceID=unitname).Create() # Temp
            except Exception as e:
             Domoticz.Debug(str(e))
             return False
          if iUnit>0:
           sval = str(temp)
           try:
            if battery is None:
             battery = 255
            Devices[iUnit].Update(nValue=0,sValue=str(sval),BatteryLevel=int(battery),SignalLevel=int(rssi))
           except:
            Domoticz.Debug(str(e))

    def SendHumSensor(self,unitname,hum,battery,rssi):
          global Devices
          iUnit = self.getdevID(unitname)
          if iUnit<0 and self.learnmode!=False: # if device does not exists in Domoticz, than create it
            try:
             iUnit = 0
             for x in range(1,256):
              if x not in Devices:
               iUnit=x
               break
             if iUnit==0:
              iUnit=len(Devices)+1
             Domoticz.Device(Name=unitname, Unit=iUnit,TypeName="Humidity",Used=0,DeviceID=unitname).Create() # Hum
            except Exception as e:
             Domoticz.Debug(str(e))
             return False
          if iUnit>0:
           sval = str(hum)
           try:
            if battery is None:
             battery = 255
            Devices[iUnit].Update(nValue=0,sValue=str(sval),BatteryLevel=int(battery),SignalLevel=int(rssi))
           except:
            Domoticz.Debug(str(e))

    def SendRainSensor(self,unitname,rain,raintotal,battery,rssi):
          global Devices
          iUnit = self.getdevID(unitname)
          if iUnit<0 and self.learnmode!=False: # if device does not exists in Domoticz, than create it
            try:
             iUnit = 0
             for x in range(1,256):
              if x not in Devices:
               iUnit=x
               break
             if iUnit==0:
              iUnit=len(Devices)+1
             Domoticz.Device(Name=unitname, Unit=iUnit,TypeName="Rain",Used=0,DeviceID=unitname).Create() # Rain
            except Exception as e:
             Domoticz.Debug(str(e))
             return False
          if iUnit>0:
           if raintotal is None:
            try:
             curval = Devices[iUnit].sValue
             prevdata = curval.split(";")
            except:
             prevdata = []
            if len(prevdata)<2:
             prevdata.append(0)
             prevdata.append(0)
            raintotal = prevdata[1]+rain
           sval = str(int(float(rain)*100))+";"+str(raintotal)
           try:
            if battery is None:
             battery = 255
            Devices[iUnit].Update(nValue=0,sValue=str(sval),BatteryLevel=int(battery),SignalLevel=int(rssi))
           except:
            Domoticz.Debug(str(e))

    def SendDistanceSensor(self,unitname,dist,battery,rssi):
          global Devices
          iUnit = self.getdevID(unitname)
          if iUnit<0 and self.learnmode!=False: # if device does not exists in Domoticz, than create it
            try:
             iUnit = 0
             for x in range(1,256):
              if x not in Devices:
               iUnit=x
               break
             if iUnit==0:
              iUnit=len(Devices)+1
             Domoticz.Device(Name=unitname, Unit=iUnit,TypeName="Distance",Used=0,DeviceID=unitname).Create() # Distance
            except Exception as e:
             Domoticz.Debug(str(e))
             return False
          if iUnit>0:
           sval = str(dist)
           try:
            if battery is None:
             battery = 255
            Devices[iUnit].Update(nValue=0,sValue=str(sval),BatteryLevel=int(battery),SignalLevel=int(rssi))
           except:
            Domoticz.Debug(str(e))

    def SendWind(self,unitname,winddirdeg,winddir,windstr,windgust,tempc,battery,rssi):
          global Devices
          iUnit = self.getdevID(unitname)
          if iUnit<0 and self.learnmode!=False: # if device does not exists in Domoticz, than create it
            try:
             iUnit = 0
             for x in range(1,256):
              if x not in Devices:
               iUnit=x
               break
             if iUnit==0:
              iUnit=len(Devices)+1
             Domoticz.Device(Name=unitname, Unit=iUnit,TypeName="Wind",Used=0,DeviceID=unitname).Create() # Wind
            except Exception as e:
             Domoticz.Debug(str(e))
             return False
          if iUnit>0:
           sval = str(winddirdeg)
           if winddir is not None:
            sval += ";"+str(winddir)
           else:
            sval += ";"
           ts = ";"
           try:
            ts = ";"+str(float(windstr)*10)
           except:
            ts = ";"
           sval += ts

           ts = ";"
           try:
            ts = ";"+str(float(windgust)*10)
           except:
            ts = ";"
           sval += ts

           if tempc is not None:
            sval += ";"+str(tempc)+";0"
           else:
            sval += ";;;0"
           try:
            if battery is None:
             battery = 255
            Devices[iUnit].Update(nValue=0,sValue=str(sval),BatteryLevel=int(battery),SignalLevel=int(rssi))
           except:
            Domoticz.Debug(str(e))

    def SendMoisture(self,unitname,moist,battery,rssi):
          global Devices
          iUnit = self.getdevID(unitname)
          if iUnit<0 and self.learnmode!=False: # if device does not exists in Domoticz, than create it
            try:
             iUnit = 0
             for x in range(1,256):
              if x not in Devices:
               iUnit=x
               break
             if iUnit==0:
              iUnit=len(Devices)+1
             Domoticz.Device(Name=unitname, Unit=iUnit,TypeName="Soil Moisture",Used=0,DeviceID=unitname).Create() # Moisture
            except Exception as e:
             Domoticz.Debug(str(e))
             return False
          if iUnit>0:
           sval = str(moist)
           try:
            if battery is None:
             battery = 255
            Devices[iUnit].Update(nValue=0,sValue=str(sval),BatteryLevel=int(battery),SignalLevel=int(rssi))
           except:
            Domoticz.Debug(str(e))

    def SendWattMeter(self,unitname,watt,battery,rssi):
          global Devices
          iUnit = self.getdevID(unitname)
          if iUnit<0 and self.learnmode!=False: # if device does not exists in Domoticz, than create it
            try:
             iUnit = 0
             for x in range(1,256):
              if x not in Devices:
               iUnit=x
               break
             if iUnit==0:
              iUnit=len(Devices)+1
             Domoticz.Device(Name=unitname, Unit=iUnit,Type=243,Subtype=29,Used=0,DeviceID=unitname).Create() # kWh
            except Exception as e:
             Domoticz.Debug(str(e))
             return False
          if iUnit>0:
           try:
            sval = str(float(watt)/1000)+";0"
           except:
            sval = "0;0"
           try:
            if battery is None:
             battery = 255
            Devices[iUnit].Update(nValue=0,sValue=str(sval),BatteryLevel=int(battery),SignalLevel=int(rssi))
           except:
            Domoticz.Debug(str(e))

    def getdirection(self,degree):
     d = float(degree)
     dirs = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']
     ix = round(d / (360. / len(dirs)))
     try:
      dir = dirs[ix % len(dirs)]
     except:
      dir = 'N'
     return dir

    def gethumstatus(self,mval):
           hstat = 0
           if int(mval)>= 50 and int(mval)<=70:
            hstat = 1
           elif int(mval)<40:
            hstat = 2
           elif int(mval)>70:
            hstat = 3
           return hstat

    def createdevname(self,m,s,c,d,t):
        tn = ""
        if s:
         tn += s
        if c:
         tn += c
        if d:
         tn += "-"+d[:16]
        if t:
         tn += "-"+t[:16]
        lplen = 25-len(tn)
        if lplen==0:
         return tn
        elif lplen<0:
         return tn[:25]
        else:
         if tn[0]!="-":
          tn = "-"+tn
         tn = m[:(25-len(tn)-1)]+tn
         return tn



global _plugin
_plugin = BasePlugin()

def onStart():
    global _plugin
    _plugin.onStart()

def onStop():
    global _plugin
    _plugin.onStop()

def onConnect(Connection, Status, Description):
    global _plugin
    _plugin.onConnect(Connection, Status, Description)

def onDeviceModified(Unit):
    global _plugin
    return

def onDisconnect(Connection):
    global _plugin
    _plugin.onDisconnect(Connection)

def onMessage(Connection, Data):
    global _plugin
    _plugin.onMessage(Connection, Data)

def onCommand(Unit, Command, Level, Color):
    global _plugin
    _plugin.onCommand(Unit, Command, Level, Color)

def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()
