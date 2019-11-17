import pycom
pycom.wifi_on_boot(False)
print("AP Disabled")
pycom.heartbeat(False)
