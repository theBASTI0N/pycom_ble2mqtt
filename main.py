from network import Bluetooth, WLAN
from umqtt.robust import MQTTClient
from binascii import hexlify
import machine
from machine import Pin
from machine import RTC
import utime
import ujson
import pycom
from bleDecoder import decode
import _thread
from config import CONFIGhome as CONFIG
import gc
import uos
import ssl


global DISCONNECTED
DISCONNECTED = 0
global CONNECTING
CONNECTING = 1
global CONNECTED
CONNECTED = 2
release =uos.uname().release
global board
board = uos.uname().sysname
global MAC
if release[:4] == '1.20':
    MAC= str.upper(hexlify(machine.unique_id(),).decode())
else:
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

def scan():
    while True:
        devices = {}
        advs = bt.get_advertisements()
        if advs :
            try:
                flT= time_stamp()
                for adv in advs:
                    devices[ hexlify( adv.mac ) ] = {
                                        #'edgeMAC' : MAC,
                                        'ts' : flT,
                                        'edgeMAC' : MAC,
                                        'mac': hexlify( adv.mac ).upper(),
                                        'rssi': adv.rssi,
                                        'data': hexlify(adv.data).decode().upper()
                                                    }
                for key, data in devices.items():
                            dMSG = {}
                            m = str(data['mac'])
                            m = m[2:-1]
                            tc =TOPIC + str.upper(m)
                            r = int(data["rssi"])
                            mFen = CONFIG.get('macFilterEn')
                            mF = CONFIG.get('macFilter')
                            RSSIen = CONFIG.get('rssiEn')
                            RSSI = CONFIG.get('rssi')
                            if RSSIen == True:
                                if r >= RSSI :
                                    if mFen == True:
                                        for i in mF:
                                            if str.upper(i) == m:
                                                msgJson = ujson.dumps( decode(m, data) )
                                                client.publish( topic=tc, msg = msgJson)
                                    else:
                                        msgJson = ujson.dumps( dMSG )
                                        client.publish( topic=tc, msg = msgJson)
                            else:
                                if mFen == True:
                                        for i in mF:
                                            if str.upper(i) == m:
                                                msgJson = ujson.dumps( decode(m, data) )
                                                client.publish( topic=tc, msg = msgJson)
                                else:
                                    msgJson = ujson.dumps( decode(m, data) )
                                    client.publish( topic=tc, msg = msgJson)
            #Needed as smaller boards run out of memory easily eg SiPy, WiPy2 etc
            except MemoryError:
                gc.collect()
                led_flash('yellow')
            #If another error is caused board restarts so scanning will begin again
            #except:
                #print("Unknown error. Performing restart")
                #machine.reset()

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
