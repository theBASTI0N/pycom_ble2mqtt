from network import Bluetooth, WLAN
from umqtt.robust import MQTTClient
from binascii import hexlify
import machine
from machine import Pin
from machine import RTC
import math
import utime
import ujson
import pycom
import _thread
from config import CONFIGhome as CONFIG
import gc
import ustruct
import uos
import ssl


global DISCONNECTED
DISCONNECTED = 0
global CONNECTING
CONNECTING = 1
global CONNECTED
CONNECTED = 2
global board
board = uos.uname().sysname
global MAC
MAC=str.upper(hexlify(WLAN().mac(),).decode())
rtc = RTC()

global ROOT_CA
ROOT_CA = '/flash/cert/ca.pem'
global CLIENT_CERT
CLIENT_CERT = '/flash/cert/cert.pem'
global PRIVATE_KEY
PRIVATE_KEY = '/flash/cert/cert.key'

TOPIC = CONFIG.get('topic1') + "/" + MAC + "/" + CONFIG.get('topic2') + "/"

#Allow easy call to flash LED different colour
def led_flash(colour):
    c = colour
    if c == 'green':
        pycom.rgbled(0x00FF00)  # Green
        utime.sleep(0.1)
        pycom.rgbled(0x000000)  # Black
        utime.sleep(0.1)
        pycom.rgbled(0x00FF00)  # Green
        utime.sleep(0.1)
        pycom.rgbled(0x000000)  # Black
    elif c == 'red':
        pycom.rgbled(0xFF0000)  # Red
        utime.sleep(0.1)
        pycom.rgbled(0x000000)  # Black
        utime.sleep(0.1)
        pycom.rgbled(0xFF0000)  # Red
        utime.sleep(0.1)
        pycom.rgbled(0x000000)  # Black
    elif c == 'yellow':
        pycom.rgbled(0x7f7f00)  # Yellow
        utime.sleep(0.1)
        pycom.rgbled(0x000000)  # Black
        utime.sleep(0.1)
        pycom.rgbled(0x7f7f00)  # Yellow
        utime.sleep(0.1)
        pycom.rgbled(0x000000)  # Black
    elif c == 'blue':
        pycom.rgbled(0x0000ff)  # blue
        utime.sleep(0.1)
        pycom.rgbled(0x000000)  # Black
        utime.sleep(0.1)
        pycom.rgbled(0x0000ff)  # Blue
        utime.sleep(0.1)
        pycom.rgbled(0x000000)  # Black
    elif c == 'purple':
        pycom.rgbled(0xff00fb)  # Purple
        utime.sleep(0.1)
        pycom.rgbled(0x000000)  # Black
        utime.sleep(0.1)
        pycom.rgbled(0xff00fb)  # Purple
        utime.sleep(0.1)
        pycom.rgbled(0x000000)  # Black

#inspired from https://github.com/Scrin/RuuviCollector
def dewPoint(temperature, relativeHumidity):
    v = math.log(relativeHumidity / 100 * equilibriumVaporPressure(temperature) / 611.2)
    return -243.5 * v / (v - 17.67)

#inspired from https://github.com/Scrin/RuuviCollector
def absoluteHumidity(temperature, relativeHumidity):
    return equilibriumVaporPressure(temperature) * relativeHumidity * 0.021674 / (273.15 + temperature)

#inspired from https://github.com/Scrin/RuuviCollector
def equilibriumVaporPressure(temperature):
    return 611.2 * math.exp(17.67 * temperature / (243.5 + temperature))

#inspired from https://github.com/Scrin/RuuviCollector
def airDensity(temperature, relativeHumidity, pressure):
    return 1.2929 * 273.15 / (temperature + 273.15) * (pressure - 0.3783 * relativeHumidity / 100 * equilibriumVaporPressure(temperature)) / 101300

def twos_complement(hexstr,bits):
     value = int(hexstr,16)
     if value & (1 << (bits-1)):
         value -= 1 << bits
     return value

def rshift(val, n):
    return (val % 0x100000000) >> n

def decode(mac, data):
    global dc
    dc= {}
    global format
    format = 0
    if '990405' in data: #Ruuvi RAWv2
        format = 5
        d = str(data)
        d = d[14:]
        temperature = twos_complement(d[2:6], 16) * 0.005
        humidity = int(d[6:10], 16) * 0.0025
        pressure = int(d[10:14], 16) + 50000
        pressure = pressure / 100
        x = twos_complement(d[14:18], 16)/1000
        y = twos_complement(d[18:22],16)/1000
        z = twos_complement(d[22:26], 16)/1000
        totalACC = math.sqrt(x * x + y * y + z * z)
        power_bin = bin(int(d[26:30], 16))
        battery_voltage = ((int(power_bin[:11], 2)) + 1600) / 1000
        tx_power = int(power_bin[11:], 2) * 2 - 40
        mC = int(d[30:32], 8)
        aH = absoluteHumidity(temperature, humidity)
        dP = dewPoint(temperature, humidity)
        airD = airDensity(temperature, humidity, pressure)

        dc = {  'f' : format,
                'temp' : temperature,
                'humidity' : humidity,
                'x' : x, 'y' :y, 'z' : z,
                'tAcc' : totalACC,
                'pressure' : pressure,
                'battery' : battery_voltage,
                'movementCounter' : mC,
                'dewPoint' : dP,
                'abHumidity' : aH,
                'airDensity' : airD,
                'tx' : tx_power,
                'mac' : mac,
                'data' : data
                }

        return
    elif '990403' in data: #Ruuvi RAWv1
        format = 3
        d = str(data)
        d = d[14:]
        humidity = int(d[2:4], 16) * 0.5
        temperature = twos_complement(d[4:6], 16) + int(d[6:8], 16) / 100
        if temperature > 128:
            temperature -= 128
            temperature = round(0 - temperature, 2)
        pressure = int(d[8:12], 16) + 50000
        pressure = pressure / 100
        x = twos_complement(d[12:16], 16)/1000
        y = twos_complement(d[16:20],16)/1000
        z = twos_complement(d[20:24], 16)/1000
        totalACC = math.sqrt(x * x + y * y + z * z)
        battery_voltage = twos_complement(d[24:28], 16)/1000
        aH = absoluteHumidity(temperature, humidity)
        dP = dewPoint(temperature, humidity)
        airD = airDensity(temperature, humidity, pressure)
        dc = {  'f' : format,
                'temp' : temperature,
                'humidity' : humidity,
                'x' : x, 'y' :y, 'z' : z,
                'tAcc' : totalACC,
                'pressure' : pressure,
                'battery' : battery_voltage,
                'dewPoint' : dP,
                'abHumidity' : aH,
                'airDensity' : airD,
                'mac' : mac,
                'data' : data}
        return
    elif 'AAFE2000' in data   :
        format = 1
        d = str(data)
        d = d[26:]
        battery_voltage = int(d[1:4], 16) / 1000
        temp1= twos_complement(d[4:6], 8)
        temp2 = int(d[6:8], 16) / 256
        temperature = temp1 + temp2
        advCnt = int(d[8:12], 16)
        secCnt = int(d[12:16], 16)

        dc = {  'f' : format,
                'temp' : temperature,
                'advCnt' : advCnt,
                'secCnt' : secCnt,
                'battery' :battery_voltage,
                'mac' : mac,
                'data' : data
                }

        return
    else:

        dc = {  'f' : format,
                'mac' : mac,
                'data' : data
                }

        return

def scan():
    while True:
        devices = {}
        advs = bt.get_advertisements()
        if advs :
            try:
                flT= time_stamp()
                for adv in advs:
                    devices[ hexlify( adv.mac ) ] = {
                                        'edgeMAC' : MAC,
                                        'ts' : flT,
                                        'Mac': hexlify( adv.mac ).upper(),
                                        'Rssi': adv.rssi,
                                        'Data': hexlify(adv.data).decode().upper()
                                                    }
                for key, data in devices.items():
                            m = str(data['Mac'])
                            m = m[2:-1]
                            dc2 = {}
                            dc2.update(data)
                            r = int(data["Rssi"])
                            mFen = CONFIG.get('macFilterEn')
                            mF = CONFIG.get('macFilter')
                            RSSIen = CONFIG.get('rssiEn')
                            RSSI = CONFIG.get('rssi')
                            if RSSIen == True:
                                if r >= RSSI :
                                    if mFen == True:
                                        for i in mF:
                                            if str.upper(i) == m:
                                                tc =TOPIC + str.upper(m)
                                                decode(m, data['Data'])
                                                if format >= 1:
                                                    dc2.update(dc)
                                                    msgJson = ujson.dumps( dc2 )
                                                    client.publish( topic=tc, msg = msgJson)
                                                else:
                                                    dc2.update(dc)
                                                    msgJson = ujson.dumps( dc2 )
                                                    client.publish( topic=tc, msg = msgJson)
                                    else:
                                        tc =TOPIC + str.upper(m)
                                        decode(m, data['Data'])
                                        if format >= 1:
                                            dc2.update(dc)
                                            msgJson = ujson.dumps( dc2 )
                                            client.publish( topic=tc, msg = msgJson)
                                        else:
                                            dc2.update(dc)
                                            msgJson = ujson.dumps( dc2 )
                                            client.publish( topic=tc, msg = msgJson)
                            else:
                                if mFen == True:
                                        for i in mF:
                                            if str.upper(i) == m:
                                                tc =TOPIC + str.upper(m)
                                                decode(m, data['Data'])
                                                if format >= 1:
                                                    dc2.update(dc)
                                                    msgJson = ujson.dumps( dc2 )
                                                    client.publish( topic=tc, msg = msgJson)
                                                else:
                                                    dc2.update(dc)
                                                    msgJson = ujson.dumps( dc2 )
                                                    client.publish( topic=tc, msg = msgJson)
                                else:
                                    tc =TOPIC + str.upper(m)
                                    decode(m, data['Data'])
                                    if format >= 1:
                                        dc2.update(dc)
                                        msgJson = ujson.dumps( dc2 )
                                        client.publish( topic=tc, msg = msgJson)
                                    else:
                                        dc2.update(dc)
                                        msgJson = ujson.dumps( dc2 )
                                        client.publish( topic=tc, msg = msgJson)
            #Needed as smaller boards run out of memory easily eg SiPy, WiPy2 etc
            except MemoryError:
                gc.collect()
                led_flash('yellow')
            #If another error is caused board restarts so scanning will begin again
            except:
                print("Unknown error. Performing restart")
                machine.reset()


def sub_cb(topic, msg):
    t = str(topic)
    m = str(msg)
    m = m[2:-1]
    if "/get/rssi" in t and m == "get": #Gets RSSI filter value
       print(CONFIG.get('rssi'))
    elif "/get/rssiEn" in t and m == "get":#Gets if RSSI filter is enabled
       print(CONFIG.get('rssiEn'))
    elif "/set/reset" in t and m == "reset":#Allows for Machine reset
       machine.reset()
    print(t[2:-1], m)

def mqtt1():#HeartBeat Client
    isSSL = CONFIG.get('ssl')
    isUSR = CONFIG.get('usr')
    state = DISCONNECTED
    global client2
    if isSSL == True and isUSR == True:
        client2 = MQTTClient( MAC + "H", CONFIG.get('host') ,user=CONFIG.get('user'), password=CONFIG.get('pass'), port=CONFIG.get('port'), keepalive=10,ssl=CONFIG.get('ssl'), ssl_params= {'cert_reqs':ssl.CERT_REQUIRED, 'ca_certs':ROOT_CA, 'certfile':CLIENT_CERT, 'keyfile': PRIVATE_KEY})
    elif isSSL == False and isUSR == True:
        client2 = MQTTClient( MAC + "H", CONFIG.get('host') ,user=CONFIG.get('user'), password=CONFIG.get('pass'), port=CONFIG.get('port'), keepalive=10, ssl=CONFIG.get('ssl'))
    else:
        client2 = MQTTClient( MAC + "H", CONFIG.get('host') ,user="", password="", port=CONFIG.get('port'), keepalive=10, ssl=CONFIG.get('ssl'))
    while state != CONNECTED:
        try:
            state = CONNECTING
            client2.connect()
            state = CONNECTED
        except:
            print('Could not establish MQTT-H connection')
            utime.sleep(0.5)
    if state == CONNECTED:
        print('MQTT-H Connected')

def heartbeat():
    while True:
        try:
            gc.collect()
            m = {}
            flT= time_stamp()
            up = utime.ticks_ms() / 1000
            mFr= gc.mem_free()
            m = {'ts' : flT,
                'board' : board,
                'edgeMAC' : MAC,
                'memFree' : mFr,
                'uptime': up,
                'ip' : ip}
            msgJson = ujson.dumps(m)
            client2.publish( topic=TOPIC + "device/heartbeat", msg =msgJson )
            led_flash('green')
            utime.sleep(0.7)
            utime.sleep(29)
        except:
            print("Unknown error. Performing restart")
            machine.reset()

def time_string(time):
    return "[{:.6f}s]".format(time)

# Formats real-time clock as text
def rtc_string(time):
    return "{}-{:0>2d}-{:0>2d}{}{:0>2d}:{:0>2d}:{:0>2d}.{:0>6d}{}".format(time[0], time[1], time[2], "T", time[3], time[4], time[5], time[6], "Z" if time[7] is None else time[7])

# If the real-time clock (RTC) has been set, provide that.
def time_stamp():
    global rtc
    if rtc is not None and rtc.synced():
        return rtc_string(rtc.now())

def WIFI():
    global wlan
    print("Attempting to connect to WiFi...")
    pycom.rgbled(0xFF0000)  # Red
    wlan = WLAN( mode=WLAN.STA)
    if CONFIG.get('wifiExt') == True:
            Pin('P12', mode=Pin.OUT)(True)
            wlan.antenna(WLAN.EXT_ANT)
            print("Using Ext for WiFi")
    wlan.connect( CONFIG.get('ssid'), auth=( WLAN.WPA2, CONFIG.get('wifiPass') ), timeout=5000 )
    while not wlan.isconnected():
        machine.idle()
    print("WiFi Connected")
    global ip
    ip = wlan.ifconfig()
    ip= ip[0]
    print("IP is: ", ip)
    led_flash('green')#Flashes THE LED Green

def mqtt2():#BLE Scan Client
    isSSL = CONFIG.get('ssl')
    isUSR = CONFIG.get('usr')
    state = DISCONNECTED
    global client
    if isSSL == True and isUSR == True:
        client = MQTTClient( MAC, CONFIG.get('host') ,user=CONFIG.get('user'), password=CONFIG.get('pass'), port=CONFIG.get('port'), ssl=CONFIG.get('ssl'), ssl_params= {'cert_reqs':ssl.CERT_REQUIRED, 'ca_certs':ROOT_CA, 'certfile':CLIENT_CERT, 'keyfile': PRIVATE_KEY})
    elif isSSL == False and isUSR == True:
        client = MQTTClient( MAC, CONFIG.get('host') ,user=CONFIG.get('user'), password=CONFIG.get('pass'), port=CONFIG.get('port'), keepalive=10, ssl=CONFIG.get('ssl'))
    else:
        client = MQTTClient( MAC, CONFIG.get('host') ,user="", password="", port=CONFIG.get('port'), keepalive=10, ssl=CONFIG.get('ssl'))
    while state != CONNECTED:
        try:
            state = CONNECTING
            client.connect()
            state = CONNECTED
        except:
            print('Could not establish MQTT connection')
            utime.sleep(0.5)
    if state == CONNECTED:
            print('MQTT Connected')

def set_rtc():
    global rtc  # Will be used outside of function
    print("Sync RTC to NTP server: " + CONFIG.get('ntp_server'))
    rtc.ntp_sync(CONFIG.get('ntp_server'))
    print("Fetching current time from " + CONFIG.get('ntp_server') + " ... ")
    rtc.ntp_sync(CONFIG.get('ntp_server'))
    while not rtc.synced(): # Wait for RTC to synchronise with the server
        machine.idle()
    print("OK")

def mqtt3():#Comms Channel
    isSSL = CONFIG.get('ssl')
    isUSR = CONFIG.get('usr')
    state = DISCONNECTED
    global client3
    if isSSL == True and isUSR == True:
        client3 = MQTTClient( MAC + "C", CONFIG.get('host') ,user=CONFIG.get('user'), password=CONFIG.get('pass'), port=CONFIG.get('port'), keepalive=10,ssl=CONFIG.get('ssl'), ssl_params= {'cert_reqs':ssl.CERT_REQUIRED, 'ca_certs':ROOT_CA, 'certfile':CLIENT_CERT, 'keyfile': PRIVATE_KEY})
        client3.set_callback( sub_cb )
    elif isSSL == False and isUSR == True:
        client3 = MQTTClient( MAC + "C", CONFIG.get('host') ,user=CONFIG.get('user'), password=CONFIG.get('pass'), port=CONFIG.get('port'), keepalive=10, ssl=CONFIG.get('ssl'))
        client3.set_callback( sub_cb )
    else:
        client3 = MQTTClient( MAC + "C", CONFIG.get('host') ,user="", password="", port=CONFIG.get('port'), keepalive=10, ssl=CONFIG.get('ssl'))
        client3.set_callback( sub_cb )
    while state != CONNECTED:
        try:
            state = CONNECTING
            client3.connect()
            state = CONNECTED
        except:
            print('Could not establish MQTT-H connection')
            utime.sleep(0.5)
    if state == CONNECTED:
        client3.subscribe( topic=TOPIC + "comms/#" )
        print('MQTT-C Connected')

def WAIT():
    print("Waiting for Message")
    while True:
        try:
            client3.wait_msg() #Checks for incoming messages
        except:
            print("Unknown error. Performing restart")
            machine.reset()

def main():
    gc.enable()
    while True:
        WIFI() #Connect to WiFi
        set_rtc() #Set RTC time
        mqtt1() #Connect Heatcheck Client
        mqtt2() #Conenct BLE Client
        mqtt3() #Connect Comms Channel Clilnet
        _thread.start_new_thread(heartbeat, ()) #Start HeartBeat loop
        print("Scanning... from: " + MAC) #Prints device MAC
        print(TOPIC) #Prints BLE data Topic
        global bt
        bt = Bluetooth()
        if CONFIG.get('btExt') == True: #If wnating to use external BLE antenna
            Pin('P12', mode=Pin.OUT)(True)
            bt.init(antenna=Bluetooth.EXT_ANT)
            print("Using Ext for Bt")
        bt.start_scan( -1 ) #Start Scanning for BLE data indefinitely
        _thread.start_new_thread(scan, ()) #Start BLE decode loop
        print("Scanning....")
        WAIT() #Start wait loop, checks for incoming messages
        print("WiFi loast Restarting....")
        machine.reset() #Should never get this ppoint

main()
