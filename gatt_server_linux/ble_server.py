#!/usr/bin/python3
# Advertises and accepts connection requests. Tracks connected/disconnected state.

import bluetooth_constants
import bluetooth_exceptions
import bluetooth_utils
import bluetooth_gatt
import random
import dbus
import dbus.exceptions
import dbus.service
import dbus.mainloop.glib
import sys
from gi.repository import GLib
sys.path.insert(0, '.')

bus = None
adapter_path = None
adv_mgr_interface = None
adv = None
connected = 0
approved_array = [0x32 , 0x62, 0x10]
mac_target = None

# much of this code was copied from or inspired by test/example-advertisement in the BlueZ source
class Advertisement(dbus.service.Object):
    PATH_BASE = '/org/bluez/example/advertisement'

    def __init__(self, bus, index, advertising_type):
        self.path = self.PATH_BASE + str(index)
        self.bus = bus
        self.ad_type = advertising_type
        self.service_uuids = None
        self.manufacturer_data = None
        self.solicit_uuids = None
        self.service_data = None
        self.local_name = 'Hello'
        self.include_tx_power = False
        self.data = None
        self.discoverable = True
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        properties = dict()
        properties['Type'] = self.ad_type
        if self.service_uuids is not None:
            properties['ServiceUUIDs'] = dbus.Array(self.service_uuids,
                                                    signature='s')
        if self.solicit_uuids is not None:
            properties['SolicitUUIDs'] = dbus.Array(self.solicit_uuids,
                                                    signature='s')
        if self.manufacturer_data is not None:
            properties['ManufacturerData'] = dbus.Dictionary(
                self.manufacturer_data, signature='qv')
        if self.service_data is not None:
            properties['ServiceData'] = dbus.Dictionary(self.service_data,
                                                        signature='sv')
        if self.local_name is not None:
            properties['LocalName'] = dbus.String(self.local_name)
        if self.discoverable is not None and self.discoverable == True:
            properties['Discoverable'] = dbus.Boolean(self.discoverable)
        if self.include_tx_power:
            properties['Includes'] = dbus.Array(["tx-power"], signature='s')

        if self.data is not None:
            properties['Data'] = dbus.Dictionary(
                self.data, signature='yv')
        print(properties)
        return {bluetooth_constants.ADVERTISING_MANAGER_INTERFACE: properties}

    def get_path(self):
        return dbus.ObjectPath(self.path)

    @dbus.service.method(bluetooth_constants.DBUS_PROPERTIES,
                         in_signature='s',
                         out_signature='a{sv}')
    def GetAll(self, interface):
        if interface != bluetooth_constants.ADVERTISEMENT_INTERFACE:
            raise bluetooth_exceptions.InvalidArgsException()
        return self.get_properties()[bluetooth_constants.ADVERTISING_MANAGER_INTERFACE]

    @dbus.service.method(bluetooth_constants.ADVERTISING_MANAGER_INTERFACE,
                         in_signature='',
                         out_signature='')
    def Release(self):
        print('%s: Released' % self.path)

def register_ad_cb():
    print('Advertisement registered OK')

def register_ad_error_cb(error):
    print('Error: Failed to register advertisement: ' + str(error))
    mainloop.quit()

# def set_connected_status(status):
#     global connected
#     if (status == 1):
#         print("connected")
#         connected = 1
#         stop_advertising()
#     else:
#         print("disconnected")
#         connected = 0
#         start_advertising()
    
# def properties_changed(interface, changed, invalidated, path):
#     if (interface == bluetooth_constants.DEVICE_INTERFACE):
#         if ("Connected" in changed):
#             set_connected_status(changed["Connected"])

# def interfaces_added(path, interfaces):
#     if bluetooth_constants.DEVICE_INTERFACE in interfaces:
#         properties = interfaces[bluetooth_constants.DEVICE_INTERFACE]
#         if ("Connected" in properties):
#             set_connected_status(properties["Connected"])

# def stop_advertising():
#     global adv
#     global adv_mgr_interface
#     print("Unregistering advertisement",adv.get_path())
#     adv_mgr_interface.UnregisterAdvertisement(adv.get_path())

def start_advertising():
    global adv
    global adv_mgr_interface
    # we're only registering one advertisement object so index (arg2) is hard coded as 0
    print("Registering advertisement",adv.get_path())
    adv_mgr_interface.RegisterAdvertisement(adv.get_path(), {},
                                        reply_handler=register_ad_cb,
                                        error_handler=register_ad_error_cb)

# create characterisitic
class TemperatureCharacteristic(bluetooth_gatt.Characteristic):
    temperature = 0             # characteristic value
    notifying = False           # notifying default state
    delta = 0 # for example only
    def __init__(self, bus, index, service):
        bluetooth_gatt.Characteristic.__init__(
                                self, bus, index,
                                bluetooth_constants.TEMPERATURE_CHR_UUID,
                                ['read','notify'],
                                service)
        self.notifying = False
        self.temperature = random.randint(0, 50)
        print("Initial temperature set to "+str(self.temperature))
        self.delta = 0
        GLib.timeout_add(1000, self.simulate_temperature)

    def simulate_temperature(self):
        self.delta = random.randint(-1, 1)
        self.temperature = self.temperature + self.delta
        if (self.temperature > 50):
            self.temperature = 50
        elif (self.temperature < 0):
            self.temperature = 0     
        if self.notifying:
            self.notify_temperature()
        GLib.timeout_add(1000, self.simulate_temperature)

    # send value from server to client when client have READ request
    def ReadValue(self, options):
        print('ReadValue in TemperatureCharacteristic called')
        print('Returning '+str(self.temperature))
        value = []
        value.append(dbus.Byte(self.temperature))
        return value
    
    # send value from server to client when client when NOTIFY is ON
    def notify_temperature(self):
        value = []
        value.append(dbus.Byte(self.temperature))
        print("notifying temperature="+str(self.temperature))
        self.PropertiesChanged(bluetooth_constants.GATT_CHARACTERISTIC_INTERFACE, { 'Value': value }, [])
        return self.notifying

    def StartNotify(self):
        print("Starting notifications")
        self.notifying = True

    def StopNotify(self):
        print("Stopping notifications")
        self.notifying = False

# create service containing characteristic
# for exammple, temperature service here has a temperature characteristic
class TemperatureService(bluetooth_gatt.Service):
# Fake micro:bit temperature service that simulates temperature sensor measurements
#ref: https://lancaster-university.github.io/microbit-docs/resources/bluetooth/bluetooth_profile.html
# temperature_period characteristic not implemented to keep things simple
    def __init__(self, bus, path_base, index):
        print("Initialising TemperatureService object")
        bluetooth_gatt.Service.__init__(self, bus, path_base, index,
                                        bluetooth_constants.TEMPERATURE_SVC_UUID, True)
        print("Adding TemperatureCharacteristic to the service")
        self.add_characteristic(TemperatureCharacteristic(bus, 0, self))

class EnergyCharacteristic(bluetooth_gatt.Characteristic):
    em_id = 0
    voltage = 0
    current = 0
    frequency = 0
    power = 0
    power_factor = 0

    def __init__(self, bus, index, service):
        bluetooth_gatt.Characteristic.__init__(
                                self, bus, index,
                                bluetooth_constants.ENERGY_CHR_UUID,
                                ['write'],
                                service)
    # receive data from client when client send WRITE request or command
    def WriteValue(self, value, options):
        energy_data = bluetooth_utils.dbus_to_python(value)
        print(energy_data)
        self.em_id = energy_data[0]
        self.voltage = energy_data[1]
        self.current = energy_data[2]
        self.power = energy_data[3]
        self.pf = energy_data[4]
        self.frequency = energy_data[5]

# class EnergyNodeInfoCharacteristic(bluetooth_gatt.Characteristic):
#     mac = 0
#     def __init__(self, bus, index, service):
#         bluetooth_gatt.Characteristic.__init__(
#                                 self, bus, index,
#                                 bluetooth_constants.ENERGY_CHR_UUID,
#                                 ['write', 'read'],
#                                 service)
#     def WriteValue(self, value, options):
#         mac = bluetooth_utils.dbus_to_python(value)
#         self.mac = mac
    
#     def check_mac(self):
#         if self.mac == mac_target:
#             print(self.mac)

class SensorCharacteristic(bluetooth_gatt.Characteristic):
    sensor_id = 0
    temp = 0
    humid = 0
    wind = 0
    pm25 = 0
    def __init__(self, bus, index, service):
        bluetooth_gatt.Characteristic.__init__(
                                self, bus, index,
                                bluetooth_constants.SENSOR_CHR_UUID,
                                ['write'],
                                service)
    def WriteValue(self, value, options):
        sensor_data = bluetooth_utils.dbus_to_python(value)
        print(sensor_data)
        self.sensor_id = sensor_data[0]
        self.temp = sensor_data[1]
        self.humid = sensor_data[2]
        self.wind = sensor_data[3]
        self.pm25 = sensor_data[4]

class FanDataCharacteristic(bluetooth_gatt.Characteristic):
    pass
class FanControlCharacteristic(bluetooth_gatt.Characteristic):
    set_speed = 0
    fan_id = 0
    notifying = False
    send_status = False
    def __init__(self, bus, index, service):
        bluetooth_gatt.Characteristic.__init__(
                                self, bus, index,
                                bluetooth_constants.FAN_CONTROL_CHR_UUID,
                                ['read', 'notify'],
                                service)
        self.fan_id = 0
        self.set_speed = 0
        self.send_status = False
        self.notifying = False
        GLib.timeout_add(1000, self.send_control)

    def ReadValue(self, options):
        print(f'Send control data to fan_id = {self.fan_id} ')
        print('Returning '+str(self.set_speed))
        value = []
        value.append(dbus.Byte(self.fan_id))
        value.append(dbus.Byte(self.set_speed))
        return value
    
    def send_control(self):
        self.fan_id = 1
        self.set_speed = 32
        # logic function

        if self.notifying == True:
            self.notify_control()
            self.send_status = False
        GLib.timeout_add(1000, self.send_control)

    def notify_control(self):
        value = []
        value.append(dbus.Byte(self.fan_id))
        value.append(dbus.Byte(self.set_speed))
        print("Notifying control fan: Fan ID: "+str(self.fan_id) + ", Speed: " +str(self.set_speed))
        self.PropertiesChanged(bluetooth_constants.GATT_CHARACTERISTIC_INTERFACE, { 'Value': value }, [])

    def StartNotify(self):
        print("Starting notify control fan")
        self.notifying = True

    def StopNotify(self):
        print("Stopping notify control fan")
        self.notifying = False
    
class ACDataCharacteristic(bluetooth_gatt.Characteristic):
    pass
class ACControlCharacteristic(bluetooth_gatt.Characteristic):
    state = 0
    ac_id = 0
    set_temp = 0
    notifying = False
    send_status = False
    def __init__(self, bus, index, service):
        bluetooth_gatt.Characteristic.__init__(
                                self, bus, index,
                                bluetooth_constants.AC_CONTROL_CHR_UUID,
                                ['read', 'notify'],
                                service)
        self.state = 2
        self.ac_id = 4
        self.set_temp = 6
        self.send_status = False
        self.notifying = False
        GLib.timeout_add(1000, self.send_control)

    def ReadValue(self, options):
        print(f'Send control data to fan_id = {self.ac_id} ')
        print('Returning '+str(self.set_temp))
        value = []
        value.append(dbus.Dictionary([self.ac_id, self.set_temp]))
        return value
    
    def send_control(self):
        # logic function

        if self.notifying == True:
            self.notify_control()
            self.send_status = False
        GLib.timeout_add(1000, self.send_control)

    def notify_control(self):
        value = []
        value.append(dbus.Byte(self.ac_id))
        value.append(dbus.Byte(self.state))
        value.append(dbus.Byte(self.set_temp))
        print("Notifying control ac: AC ID: "+str(self.ac_id) + ", State: " + str(self.state) + ", Speed: " +str(self.set_temp))
        self.PropertiesChanged(bluetooth_constants.GATT_CHARACTERISTIC_INTERFACE, { 'Value': value }, [])

    def StartNotify(self):
        print("Starting notify control AC")
        self.notifying = True

    def StopNotify(self):
        print("Stopping notify control AC")
        self.notifying = False

class ThingService(bluetooth_gatt.Service):
    def __init__(self, bus, path_base, index):
        print("Initialising TemperatureService object")
        bluetooth_gatt.Service.__init__(self, bus, path_base, index,
                                        bluetooth_constants.THINGS_SVC_UUID, True)
        print("Adding SensorCharacteristic to the service")
        self.add_characteristic(SensorCharacteristic(bus, 0, self))
        print("Adding EnergyCharacteristic to the service")
        self.add_characteristic(EnergyCharacteristic(bus, 1, self))
        print("Adding FanControlCharacteristic to the service")
        self.add_characteristic(FanControlCharacteristic(bus, 2, self))
        print("Adding ACControlCharacteristic to the service")
        self.add_characteristic(ACControlCharacteristic(bus, 3, self))

# setup application layer   
class Application(dbus.service.Object):
    """
    org.bluez.GattApplication1 interface implementation
    """
    def __init__(self, bus):
        self.path = '/'
        self.services = []
        dbus.service.Object.__init__(self, bus, self.path)
        print("Adding TemperatureService to the Application")
        self.add_service(TemperatureService(bus, '/org/bluez/example', 0))
        print("Adding ThingService to the Application")
        self.add_service(ThingService(bus, '/org/bluez/example', 1))
        
    def get_path(self):
        return dbus.ObjectPath(self.path)
    
    def add_service(self, service): 
        self.services.append(service)
    
    @dbus.service.method(bluetooth_constants.DBUS_OM_IFACE, out_signature='a{oa{sa{sv}}}')
    def GetManagedObjects(self):
        response = {}
        print('GetManagedObjects')

        for service in self.services:
            print("GetManagedObjects: service="+service.get_path())
            response[service.get_path()] = service.get_properties()
            chrcs = service.get_characteristics()
            for chrc in chrcs:
                response[chrc.get_path()] = chrc.get_properties()
                descs = chrc.get_descriptors()
                for desc in descs:
                    response[desc.get_path()] = desc.get_properties()

        return response
    
def register_app_cb():
    print('GATT application registered')
def register_app_error_cb(error):
    print('Failed to register application: ' + str(error))
    mainloop.quit()
    
dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
bus = dbus.SystemBus()
# we're assuming the adapter supports advertising
adapter_path = bluetooth_constants.BLUEZ_NAMESPACE + bluetooth_constants.ADAPTER_NAME
print(adapter_path)

bus.add_signal_receiver

# bus.add_signal_receiver(properties_changed,
#         dbus_interface = bluetooth_constants.DBUS_PROPERTIES,
#         signal_name = "PropertiesChanged",
#         path_keyword = "path")

# bus.add_signal_receiver(interfaces_added,
#         dbus_interface = bluetooth_constants.DBUS_OM_IFACE,
#         signal_name = "InterfacesAdded")

adv_mgr_interface = dbus.Interface(bus.get_object(bluetooth_constants.BLUEZ_SERVICE_NAME,adapter_path), bluetooth_constants.ADVERTISING_MANAGER_INTERFACE)
adv = Advertisement(bus, 0, 'peripheral')
start_advertising()
print("Advertising as "+adv.local_name)

mainloop = GLib.MainLoop()

app = Application(bus)
print('Registering GATT application...')

service_manager = dbus.Interface(
        bus.get_object(bluetooth_constants.BLUEZ_SERVICE_NAME, adapter_path),
        bluetooth_constants.GATT_MANAGER_INTERFACE)

service_manager.RegisterApplication(app.get_path(), {},
                                reply_handler=register_app_cb,
                                error_handler=register_app_error_cb)
mainloop.run()
