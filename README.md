# pycom_ble2mqtt
BLE to MQTT application for Pycom boards

This application is designed to turn your pycom board into a functioning BLE
gateway. It creates a topic that is specific to each tag for ease of
subscribing and using the data.

# Working Boards

This application shoud be able to work on most Pycom boards with it tested on:
  * WiPy3
  * SiPy

With the SiPy having much less memory then the WiPy3 no performance issue have
been noticed on the SiPy.

## Decoding data

This applications allows for the decoding of some BLE data. Meaning once received
the data can be easily pushed into a database.

In the published message the format type is send as "f".
The following types of data can be decoded:
  * Format 0 - Any BLE data that is not decoded by the application.
  * Format 1 - Eddystone TLM data.
  * Format 3 - Ruuvi RAWv1
  * Format 5 - Ruuvi RAWv2


## Publishing Topics

These topics send data and cannot receive it.
This application supports publishing these advertisements over MQTT.

* Topic1/boardMAC/topic2/BLEMAC
  Example:
  home/3C71BF877D48/beacon/E20B1593499E

  Publishing a mesasges like:
  ```json

  {"x": 0.024, "z": 1.008, "f": 5, "temp": 26.14,
    "ts": "2019-11-17T02:39:31.261467Z", "Mac": "E20B1593499E", "edgeMAC": "3C71BF877D48",
    "battery": 2.025, "Rssi": -86, "y": 0.012, "tAcc": 1.008357, "pressure": 1018.39,
    "tx": -6, "humidity": 57.1375,
    "Data": "0201061BFF990405146C5947CA7F0018000C03F0A4B4B02D06E20B1593499E03190000020A000D09436F72655461675F3439396500000000000000000000"}

  ```
* Topic1/boardMAC/topic2/heartbeat
    Example:
    home/3C71BF877D48/beacon/device/heartbeat
    Publishing a message like:
    ```json

  {"uptime": 147434.0, "ts": "2019-11-17T02:40:48.766209Z",
    "edgeMAC": "3C71BF877D48", "memFree": 2538688, "board": "WiPy"}

    ```

## Subscribing Topic

The application has the ability to subscribe to a topic and receive message if
sent to the board. However performance is limited to the reliabilty of the MQTT
connection which is a limitation of the at the moment.

At this stage this is not used, but can be tested to print a message if wanted.

## Configuration

The configuration file is located in the main directory being named config.py.
It contains all of the different configuration options.

Multiple configurations can be entered and called upon in the main application
on line 12. By replacing "CONFIGhome" with the name of your config.

Example:
```python

CONFIGhome = {
  "broker" : "0.0.0.0",
  "ssl" : False,
  "port" : 1883,
  "usr" : True,
  "mqttuser" : "username",
  "mqttpass" : "password",
  "topic1" : "home",
  "topic2" : "beacon",
  "ssid" : "ssid",
  "wifiPass" : "wifipassword",
  "wifiExt" : False,
  "ntp_server" : "time.google.com",
  "rssiEn" : False,
  "rssi" : -127,
  "macFilterEn" : False,
  "macFilter" : [ "c0bb722a568e", "aabbccddeeff", "aabbccddeef1", "aabbccddeef2"],
  "btExt" : False
}

```
* broker = The IP address of your MQTT broker.
* ssl = If wanting to use a SSL conenction to you broker.
* port = 1883 is the standard MQTT port, if using SSL 8883 is standard
* usr = Enable this if your broker requires a username and password to connect
* mqttuser = Username required for broker conenction
* mqttpass = Password required for broker connection
* topic1 = can be used to identifiy each gateway further. For example "kitchen"
* topic2 = used to publish ble Data
* ssid = WiFi SSID
* wifiPass = WiFi password
* wifiExt = Enable this is wanting to use external WiFi antenna
* ntp_server = Default checks time with google NTP server
* rssiEn = Enable if RSSI filtering is wanted
* rssi = Set the RSSI filter for example -40 would be almost touching the board
* macFilterEn = Enable this if you want to only send data on specific BLE beacons
* macFilter = The list of ble beacons to send data for
* btExt = Enable this if you want to use the external antenna for BLE





-------------------------------------------------------------------------------------------------------------------
## Known Limitations
I have found that the limitations of the application are towards the MQTT implementation on the board itself. With loss of connections to broker happening on occassion. Whilst there is data going through both the BLE and Heartbeat client the conenction seems to be strong however the subscribing to a topic always causes issues.

I have tried using the BLE client which is almost always TX messages to subscribe to the comms topic and issues would still occur after some time.

SSL performance is unreliable and slow
