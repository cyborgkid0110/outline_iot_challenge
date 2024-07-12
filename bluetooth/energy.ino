#include <PZEM004Tv30.h>
#define VCC_PIN 19
#define ACTIVATE_BLE 4
#define LED_BUILTIN_PIN 2
#include "BLEDevice.h"

PZEM004Tv30 pzema(Serial2, 17, 16); // GP1016 to Tx PZEM004; GP1017 to Rx PZEM004
const uint8_t EM_ID = 1;

// The remote service we wish to connect to.
static BLEUUID serviceUUID("ca299713-6a0e-4ed5-1111-447a42d26fc2");
// The characteristics of the remote service we are interested in.
static BLEUUID charUUID("ca299713-6a0e-4ed5-0003-447a42d26fc2");

static boolean doConnect = false;
static boolean connected = false;
static boolean doScan = false;
static BLEAdvertisedDevice *myDevice;
BLERemoteCharacteristic *pRemoteChar; 
bool scan_host = true;



static void notifyCallback(BLERemoteCharacteristic *pBLERemoteCharacteristic, uint8_t *pData, size_t length, bool isNotify) {
  if (pBLERemoteCharacteristic->getUUID().toString() == charUUID.toString()) {
    Serial.print("Notify callback for characteristic 1 ");
    Serial.print(pBLERemoteCharacteristic->getUUID().toString().c_str());
    Serial.print(" of data length ");
    Serial.println(length);
    Serial.print("data: ");
    Serial.write(pData, length);
    Serial.println();
  }
}

class MyClientCallback : public BLEClientCallbacks {
  void onConnect(BLEClient *pclient) {}

  void onDisconnect(BLEClient *pclient) {
    connected = false;
    Serial.println("onDisconnect");
  }
};

bool connectToServer() {
  Serial.print("Forming a connection to ");
  Serial.println(myDevice->getAddress().toString().c_str());

  BLEClient *pClient = BLEDevice::createClient();
  Serial.println(" - Created client");

  pClient->setClientCallbacks(new MyClientCallback());
  // Connect to the remove BLE Server.
  pClient->connect(myDevice);  // if you pass BLEAdvertisedDevice instead of address, it will be recognized type of peer device address (public or private)
  Serial.println(" - Connected to server");
  pClient->setMTU(517);  //set client to request maximum MTU from server (default is 23 otherwise)

  // Obtain a reference to the service we are after in the remote BLE server.
  BLERemoteService *pRemoteService = pClient->getService(serviceUUID);
  if (pRemoteService == nullptr) {
    Serial.print("Failed to find our service UUID: ");
    Serial.println(serviceUUID.toString().c_str());
    pClient->disconnect();
    return false;
  }

  Serial.println(" - Found our service");
  connected = true;
  if (connectCharacteristic(pRemoteService, charUUID) == false)
    connected = false;
  
  if (connected == false) {
    pClient->disconnect();
    Serial.println("There is at least 1 characteristic UUID not found");
    return false;
  }

  pRemoteChar = pRemoteService->getCharacteristic(charUUID);
  return true;
}

bool connectCharacteristic(BLERemoteService* pRemoteService, BLEUUID charUUID) {
  // Obtain a reference to the characteristic in the service of the remote BLE server.
  static BLERemoteCharacteristic *pRemoteCharacteristic;
  pRemoteCharacteristic = pRemoteService->getCharacteristic(charUUID);
  if (pRemoteCharacteristic == nullptr) {
    Serial.print("Failed to find our characteristic UUID: ");
    Serial.println(charUUID.toString().c_str());
    return false;
  }
  Serial.println(" - Found our characteristic");

  if (pRemoteCharacteristic->canNotify()) {
    pRemoteCharacteristic->registerForNotify(notifyCallback);
  }
  return true;
}
/**
 * Scan for BLE servers and find the first one that advertises the service we are looking for.
 */
class MyAdvertisedDeviceCallbacks : public BLEAdvertisedDeviceCallbacks {
  /**
   * Called for each advertising BLE server.
   */
  void onResult(BLEAdvertisedDevice advertisedDevice) {
    Serial.print("BLE Advertised Device found: ");
    Serial.println(advertisedDevice.toString().c_str());

    // We have found a device, let us now see if it contains the service we are looking for.
    if (advertisedDevice.haveServiceUUID()) {
      Serial.println("Able to read service UUID...");
    }

    if (advertisedDevice.getAddress().toString() == "d8:3a:dd:65:df:eb") {
      Serial.println("FOUND");
      BLEDevice::getScan()->stop();
      myDevice = new BLEAdvertisedDevice(advertisedDevice);
      doConnect = true;
      doScan = true;

    }  // Found our server
  }  // onResult
};  // MyAdvertisedDeviceCallbacks

void BLE_Scaning() {
  BLEScan *pBLEScan = BLEDevice::getScan();
  pBLEScan->setAdvertisedDeviceCallbacks(new MyAdvertisedDeviceCallbacks());
  pBLEScan->setInterval(1349);
  pBLEScan->setWindow(449);
  pBLEScan->setActiveScan(true);
  pBLEScan->start(10, false);
}

void setup() {
  pinMode(VCC_PIN, OUTPUT);
  digitalWrite(VCC_PIN, HIGH);
  BLEDevice::init("");
  pinMode(LED_BUILTIN_PIN, OUTPUT);
  pinMode(ACTIVATE_BLE, INPUT_PULLUP);
  Serial.begin(115200);
  Serial.println("\nPZEM004T Testing");
  delay(2000);
}

void loop() {
  while(scan_host) {
    scan_host = digitalRead(ACTIVATE_BLE);
    if (!scan_host) {
      BLE_Scaning();
    }
  }

  if (doConnect == true) {
    if (connectToServer()) {
      Serial.println("We are now connected to the BLE Server.");
    } else {
      Serial.println("We have failed to connect to the server; there is nothing more we will do.");
    }
    doConnect = false;
  }

  if (connected) {
    digitalWrite(LED_BUILTIN_PIN, HIGH); 
    double voltage = pzema.voltage();
    double current = pzema.current();
    double power = pzema.power();
    double pf = pzema.pf();
    double frequency = pzema.frequency();
    if (isnan(voltage)) {
      voltage = 0; // invalid value
    }
    if (isnan(current)) {
      current = 0;
    }
    if (isnan(power)) {
      power = 0;
    }
    if (isnan(pf)) {
      pf = 0;
    }
    if (isnan(frequency)) {
      frequency = 0;
    }
    double data[5] = {voltage, current, power, pf, frequency};
    uint8_t newValue[21];
    newValue[0] = EM_ID;
    uint8_t count = 1;
    for (int i = 0; i < 5; i++) {
      uint8_t* bytes = (uint8_t *)&data[i];
      for (int j = 0; j < 3; j++) {
        newValue[count] = bytes[j];
        count++;
      }
    }
    // Set the characteristic's value to be the array of bytes that is actually a string.
    pRemoteChar->writeValue(newValue, 21);
  } else if (doScan) {
    BLEDevice::getScan()->start(0);  // this is just example to start scan after disconnect, most likely there is better way to do it in arduino
  }

  if (!connected) {
    digitalWrite(LED_BUILTIN_PIN, LOW);
  }

  delay(1000); 
}
