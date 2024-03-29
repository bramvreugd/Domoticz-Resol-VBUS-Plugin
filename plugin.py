# VBUS plugin
#
# Author: Bramv, 2021
#
#   This connects with a vbus device and reads the values. Vbus is a protol used by solar installation by Resol
#
#
# todo remove need of json live data server and connect directly to resol-vbus library
# test if serial is working this is only tested over tcp/ip

"""
<plugin key="VBUS" name="VBUS solar monitor" author="Bramv" version="1.2.0" externallink="https://www.github.com">
    <description>
        <h2>VBUS solar connection Resol</h2><br/>
        Will hit the supplied URL every 2 heartbeats in the request protocol.  Redirects are handled.
        You need VBUS and the example "json-live-data-server" running.
        https://github.com/danielwippermann/resol-vbus
    </description>
    <params>
        <param field="Address" label="IP Address" width="200px" required="true" default="127.0.0.1"/>
        <param field="Port" label="Port" width="30px" required="true" default="9090"/>
        <param field="Mode6" label="Debug" width="150px">
            <options>
                <option label="None" value="0"  default="true" />
                <option label="Python Only" value="2"/>
                <option label="Basic Debugging" value="62"/>
                <option label="Basic+Messages" value="126"/>
                <option label="Connections Only" value="16"/>
                <option label="Connections+Python" value="18"/>
                <option label="Connections+Queue" value="144"/>
                <option label="All" value="1"/>
            </options>
        </param>
    </params>
</plugin>
"""
import Domoticz
import json
import datetime
from datetime import datetime

class BasePlugin:
    httpConn = None
    runAgain = 0          # start immidiate. next time  use 6
    disconnectCount = 0
    sProtocol = "HTTP"
    previousDate = 0

    def __init__(self):
        return

    def onStart(self):
        Domoticz.Log("onStart.")

        if Parameters["Mode6"] != "0":
            Domoticz.Debugging(int(Parameters["Mode6"]))
            DumpConfigToLog()

        self.httpConn = Domoticz.Connection(Name="ResolConn", Transport="TCP/IP", Protocol="HTTP", Address=Parameters["Address"], Port=Parameters["Port"])
        self.httpConn.Connect()
        Domoticz.Log("onStart connected")

    def onStop(self):
        Domoticz.Log("onStop - Plugin is stopping.")

    def onConnect(self, Connection, Status, Description):
        if (Status == 0):
            Domoticz.Debug("Connected successfully.")
            sendData = { 'Verb' : 'GET',
                         'URL'  :  '/api/v1/live-data',
                         'Headers' : { 'Content-Type': 'text/xml; charset=utf-8', \
                                       'Connection': 'keep-alive', \
                                       'Accept': 'Content-Type: text/html; charset=UTF-8', \
                                       'Host': Parameters["Address"]+":"+Parameters["Mode1"], \
                                       'User-Agent':'Domoticz/1.0' }
                       }
            Connection.Send(sendData)
            #Connection.Send(sendData)
        else:
            Domoticz.Error("Failed to connect ("+str(Status)+") to: "+Parameters["Address"]+":"+Parameters["Mode1"]+" with error: "+Description)

    def UpdateDevice(self,Unit, nValue, sValue):
       # Make sure that the Domoticz device still exists (they can be deleted) before updating it
       if (Unit in Devices):
           if(Devices[Unit].LastUpdate):
               lastupdate = datetime.strptime(Devices[Unit].LastUpdate, '%Y-%m-%d %H:%M:%S')

               #lastupdate = datetime.datetime.fromtimestamp(time.mktime(time.strptime(Devices[Unit].lastUpdate, '%Y-%m-%d %H:%M:%S')))
               now= datetime.now()
               diff=now-lastupdate
               if (Devices[Unit].nValue != nValue) or (Devices[Unit].sValue != sValue) or (diff.total_seconds() >300):
                   Devices[Unit].Update(nValue, str(sValue))
           else:
              Devices[Unit].Update(nValue, str(sValue))
       return

    def processResponse(self,Response):
        #Domoticz.Log("resol response:" + str(Response))

        statusMesg =''
        HeatInTotal=-1
        Power=-1

        for counter in Response:
            #Domoticz.Log("resol counter:" + str(counter))

            if (counter['id']!="00_0010_1001_10_0100_000_4_0"):
                cntr_id= counter['id'][:20]
                cntr_key=int(counter['id'][21:24])
                cntr_type=counter['id'][25:26]   # 1  bool  2 float   4 = int
                cntr_bit=counter['id'][27:]
                cntr_name=counter['name']
                cntr_rawvalue=counter['rawValue']
                if(cntr_name[:5]=="Error" or cntr_name[:7]=="Warning"):
                    cntr_key=103       # place error en warning in same device

                if(cntr_id=="00_0010_1011_10_0100"):
                    if(cntr_name=="Heat In total"):
                       cntr_key=100
                    elif(cntr_name=="Volume in total"):
                       cntr_key=101
                    elif(cntr_name=="Power"):     # power and heat are also combined in total heat
                       cntr_key=102
                    else:
                       cntr_key=-1

                if not (cntr_key in Devices) and (cntr_bit=='0') and cntr_key!=-1:
                    if(cntr_name[:4]=='Temp'):
                       typeName="Temperature"
                    if(cntr_name[:4]=='Flow'):
                       typeName="Waterflow"
                    if(cntr_name[:4]=='Pres'):
                       typeName="Pressure"
                    if(cntr_name[:4]=='Pump'):
                       typeName="Switch"
                    if(cntr_name[:3]=='PWM'):
                       typeName="Percentage"
                    if(cntr_name=='Error mask' or cntr_name=='Warning mask'):
                       typeName='Text'
                       cntr_name='VBUS status'
                    if(cntr_name=="Heat In total"):
                       typeName='kWh'
                    if(cntr_name=="Volume in total"):
                       typeName="counter"
                       Domoticz.Device(Name=cntr_name, Unit=int(cntr_key), Type=113,Subtype=0,Switchtype=2).Create()
                    elif(cntr_name=="Power"):
                       Domoticz.Device(Name=cntr_name, Unit=int(cntr_key), Type=248,Subtype=1, Image=0).Create()
                    else:
                        if(int(cntr_key)!="-1"):
                            Domoticz.Device(Name=cntr_name, Unit=int(cntr_key), TypeName=typeName).Create()

                if (cntr_key in Devices) and cntr_key!=-1 and (cntr_bit=='0'):
                    if(cntr_name=="Heat In total"):
                        HeatInTotal=round(cntr_rawvalue,2)
                    elif(cntr_name=="Power"):
                        Power=round(cntr_rawvalue*1000,2) # convert kw to watt
                    elif(cntr_name[:4]=='Flow'):
                        self.UpdateDevice(cntr_key,0,str(round(cntr_rawvalue/60,2))) # convert liter/hour to liter/min
                    elif(cntr_name[:6]=='Volume'):
                        self.UpdateDevice(cntr_key,0,str(cntr_rawvalue)) # no nvalue needed
                    elif(cntr_name[:4]=='Temp'):
                        self.UpdateDevice(cntr_key,0,str(round(cntr_rawvalue,2))) # temperatures can be adjusted
                        #  +Devices[cntr_key].Adjustment,2)    this should be implemented but does not work reuires domoticzex platform
                    elif(cntr_name[:4]=='Pres'):
                        self.UpdateDevice(cntr_key,0,str(round(cntr_rawvalue,2))) # pressure
                    elif(cntr_name[:4]=='Pump'):
                        if(cntr_rawvalue==100):
                           self.UpdateDevice(cntr_key,1,"100")
                        elif(cntr_rawvalue==0):
                           self.UpdateDevice(cntr_key,0,"0")
                        else:
                           self.UpdateDevice(cntr_key,2,str(round(cntr_rawvalue,2)))
                    else:
                        Domoticz.Log("resol update "+ str(cntr_key))
                        Domoticz.Log("val:" + str(cntr_rawvalue))
                        Domoticz.Log(str(round(cntr_rawvalue,2)))
                        self.UpdateDevice(cntr_key,cntr_rawvalue,str(round(cntr_rawvalue,2)))

                if (cntr_bit!='0') and (cntr_rawvalue !=0):
                    statusMesg = statusMesg + cntr_name
        if(Power!=-1) or (HeatInTotal!=-1) :
            self.UpdateDevice(102,0,str(max(Power,0)))
            self.UpdateDevice(100,0,str(Power)+";"+str(max(HeatInTotal,0)))

        if(statusMesg!=''):
            self.UpdateDevice(103,0,statusMesg)

    def onMessage(self, Connection, Data):
        #DumpHTTPResponseToLog(Data)

        strData = Data["Data"].decode("utf-8", "ignore").strip()
        Status = int(Data["Status"])

        if (Status == 200):
            if ((self.disconnectCount & 1) == 1):
                Domoticz.Debug("Good Response received from vbus, Disconnecting.")
                if(self.httpConn!=None):
                   self.httpConn.Disconnect()
            else:
                Domoticz.Debug("Good Response received from vbus, Dropping connection.")
                self.httpConn = None
            self.disconnectCount = self.disconnectCount + 1
            Response = json.loads( strData )
            resolDate=Response[0]['rawValue']
            #Domoticz.Log("Resol VBUS returned response:"+str(Response)+'date:'+str(resolDate)+" "+str(self.previousDate))

            if(resolDate!=self.previousDate):
                # date is diff so procees the page
                self.previousDate=resolDate

                #Domoticz.Log("Resol date new")
                self.processResponse(Response)
                #Domoticz.Log("Resol date new done processresponse")

        elif (Status == 302):
            Domoticz.Log("VBUS returned a Page Moved Error.")
            sendData = { 'Verb' : 'GET',
                         'URL'  : Data["Headers"]["Location"],
                         'Headers' : { 'Content-Type': 'text/xml; charset=utf-8', \
                                       'Connection': 'keep-alive', \
                                       'Accept': 'Content-Type: text/html; charset=UTF-8', \
                                       'Host': Parameters["Address"]+":"+Parameters["Mode1"], \
                                       'User-Agent':'Domoticz/1.0' },
                        }
            Connection.Send(sendData)
        elif (Status == 400):
            Domoticz.Error("VBUS returned a Bad Request Error.")
        elif (Status == 500):
            Domoticz.Error("VBUS returned a Server Error.")
        else:
            Domoticz.Error("VBUS returned a status: "+str(Status))

    def onCommand(self, Unit, Command, Level, Hue):
        Domoticz.Debug("onCommand called for Unit " + str(Unit) + ": Parameter '" + str(Command) + "', Level: " + str(Level))

    def onDisconnect(self, Connection):
        Domoticz.Log("onDisconnect called for connection to: "+Connection.Address+":"+Connection.Port)

    def onHeartbeat(self):
        Domoticz.Debug("onHeartbeat:"+str(self.runAgain))
        if (self.httpConn != None and (self.httpConn.Connecting() or self.httpConn.Connected())):
            Domoticz.Debug("onHeartbeat called, Connection is alive.")
        else:
            self.runAgain = self.runAgain - 1
            if self.runAgain <= 0:
                if (self.httpConn == None):
                    self.httpConn = Domoticz.Connection(Name=self.sProtocol+" Test", Transport="TCP/IP", Protocol=self.sProtocol, Address=Parameters["Address"], Port=Parameters["Port"])
                self.httpConn.Connect()
                self.runAgain = 1
            else:
                Domoticz.Debug("onHeartbeat called, run again in "+str(self.runAgain)+" heartbeats.")

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

def onMessage(Connection, Data):
    global _plugin
    _plugin.onMessage(Connection, Data)

def onCommand(Unit, Command, Level, Hue):
    global _plugin
    _plugin.onCommand(Unit, Command, Level, Hue)

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
def LogMessage(Message):
    if Parameters["Mode6"] == "File":
        f = open(Parameters["HomeFolder"]+"http.html","w")
        f.write(Message)
        f.close()
        Domoticz.Log("File written")

def DumpConfigToLog():
    for x in Parameters:
        if Parameters[x] != "":
            Domoticz.Debug( "'" + x + "':'" + str(Parameters[x]) + "'")
    Domoticz.Debug("Device count: " + str(len(Devices)))
    for x in Devices:
        Domoticz.Debug("Device:           " + str(x) + " - " + str(Devices[x]))
        Domoticz.Debug("Device ID:       '" + str(Devices[x].ID) + "'")
        Domoticz.Debug("Device Name:     '" + Devices[x].Name + "'")
        Domoticz.Debug("Device nValue:    " + str(Devices[x].nValue))
        Domoticz.Debug("Device sValue:   '" + Devices[x].sValue + "'")
        Domoticz.Debug("Device LastLevel: " + str(Devices[x].LastLevel))
    return

def DumpHTTPResponseToLog(httpResp, level=0):
    if (level==0): Domoticz.Debug("HTTP Details ("+str(len(httpResp))+"):")
    indentStr = ""
    for x in range(level):
        indentStr += "----"
    if isinstance(httpResp, dict):
        for x in httpResp:
            if not isinstance(httpResp[x], dict) and not isinstance(httpResp[x], list):
                Domoticz.Debug(indentStr + ">'" + x + "':'" + str(httpResp[x]) + "'")
            else:
                Domoticz.Debug(indentStr + ">'" + x + "':")
                DumpHTTPResponseToLog(httpResp[x], level+1)
    elif isinstance(httpResp, list):
        for x in httpResp:
            Domoticz.Debug(indentStr + "['" + x + "']")
    else:
        Domoticz.Debug(indentStr + ">'" + x + "':'" + str(httpResp[x]) + "'")
