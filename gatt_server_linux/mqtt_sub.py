import paho.mqtt.client as mqtt
from getmac import get_mac_address

MAC = get_mac_address()
print(MAC) # testing only

# Define the MQTT broker details
broker = "192.168.91.7"
port = 1883

# Define the topic to subscribe to
topic = "test/topic"

# Callback function when a message is received
def on_message(client, userdata, message):
    print(f"Received message '{message.payload.decode()}' on topic '{message.topic}'")

# Callback function when the client connects to the broker
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT Broker!")
        client.subscribe(topic)  # Subscribe to the topic after connecting
    else:
        print(f"Failed to connect, return code {rc}")

# Callback function when the client subscribes to a topic
def on_subscribe(client, userdata, mid, granted_qos):
    print(f"Subscribed to topic: {topic}")

# Create a new MQTT client instance
client = mqtt.Client()

# Attach the callback functions
client.on_message = on_message
client.on_connect = on_connect
client.on_subscribe = on_subscribe

# Connect to the broker
client.connect(broker, port)

# Start the loop to process received messages
client.loop_forever()

# Note: client.loop_forever() keeps the script running and processes callbacks,
# so there's no need for an explicit while True loop.
