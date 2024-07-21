import time
import threading
import mariadb
import paho.mqtt.client as mqtt
import json
import global_var
import pickle
from getmac import get_mac_address

MAC = get_mac_address()     # MAC address here

# Cấu hình MySQL
MYSQL_HOST = 'localhost' # change w.r.t. gateway
MYSQL_USER = 'giang_mariadb'
MYSQL_PASSWORD = 'k'
MYSQL_DATABASE = 'iot_clg_db'

# Cấu hình MQTT
MQTT_BROKER = '172.20.10.13' # change to local IP server
MQTT_PORT = 1883

# publish topic
MQTT_GATEWAY_REGISTRY =         'server/connect'
MQTT_TOPIC_CONNECT_KEY_ACK =    'server/connect_key_ack'
MQTT_SENSOR_NODE_CONNECT =      'server/sensor/connect'
MQTT_ENERGY_NODE_CONNECT =      'server/energy/connect'
MQTT_FAN_NODE_CONNECT =         'server/fan/connect'
MQTT_AC_NODE_CONNECT =          'server/ac/connect'
MQTT_SENSOR_SEND_NODE_INFO_ACK =    'server/sensor/node_info_ack'
MQTT_ENERGY_SEND_NODE_INFO_ACK =    'server/energy/node_info_ack'
MQTT_FAN_SEND_NODE_INFO_ACK =       'server/fan/node_info_ack'
MQTT_AC_SEND_NODE_INFO_ACK =        'server/ac/node_info_ack'
MQTT_TOPIC_KEEPALIVE_ACK =          'server/keepalive_ack'

MQTT_TOPIC_PMV_DATA =           'server/pmv_data'
MQTT_TOPIC_SENSOR_DATA =        'server/sensor_data'
MQTT_TOPIC_FAN_DATA =           'server/fan_data'
MQTT_TOPIC_EM_DATA =            'server/energy_measure_data'
MQTT_TOPIC_AC_DATA =            'server/air_conditioner_data'

MQTT_TOPIC_CONTROL_FAN_ACK =    'server/fan/control_ack'
MQTT_TOPIC_CONTROL_AC_ACK =     'server/ac/control_ack'

# subscribe topic
MQTT_GATEWAY_LINKING =          'gateway/permission'
MQTT_TOPIC_CONNECT_KEY =        'gateway/connect_key'
MQTT_TOPIC_KEEPALIVE =          'gateway/keepalive'
MQTT_SENSOR_SEND_NODE_INFO =    'gateway/sensor/node_info'
MQTT_ENERGY_SEND_NODE_INFO =    'gateway/energy/node_info'
MQTT_FAN_NODE_SEND_NODE_INFO =  'gateway/fan/node_info'
MQTT_AC_SEND_NODE_INFO =        'gateway/ac/node_info'

MQTT_SEND_ENV_PARAMS =          'gateway/env_params'
MQTT_TOPIC_CONTROL_FAN =        'gateway/fan/control'
MQTT_TOPIC_CONTROL_AC =         'gateway/ac/control'

fan_id_target = None
set_speed_target = None
set_temp_target = None
state_target = None
ac_id_target = None
actuator_control_signal = None

# Hàm lấy dữ liệu từ MySQL
def fetch_data_from_mysql(query):
    try:
        conn = mariadb.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE
        )
        cursor = conn.cursor()
        cursor.execute(query)
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return result
    except mariadb.Error as err:
        print(f"Error: {err}")
        return None
    
def create_connection():
    try:
        connection = mariadb.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE
        )

        return connection
        
    except mariadb.Error as e:
        print("Error while connecting to MySQL:", e)
        return None
    
# Connect to MQTT broker
def connect_mqtt():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    return client

def run_mqtt_client():
    client.loop_forever()

# Callback khi kết nối thành công tới MQTT Broker
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT Broker!")
        client.subscribe(MQTT_GATEWAY_LINKING)
        client.subscribe(MQTT_TOPIC_CONNECT_KEY)
        client.subscribe(MQTT_TOPIC_KEEPALIVE)
        client.subscribe(MQTT_SENSOR_SEND_NODE_INFO)
        client.subscribe(MQTT_ENERGY_SEND_NODE_INFO)
        client.subscribe(MQTT_FAN_NODE_SEND_NODE_INFO)
        client.subscribe(MQTT_AC_SEND_NODE_INFO)
        client.subscribe(MQTT_SEND_ENV_PARAMS)
        client.subscribe(MQTT_TOPIC_CONTROL_FAN)
        client.subscribe(MQTT_TOPIC_CONTROL_AC)
    else:
        print(f"Failed to connect, return code {rc}")

# Callback khi ngắt kết nối với MQTT Broker
def on_disconnect(client, userdata, rc):
    if rc != 0:
        print("Unexpected disconnection.")
    else:
        print("Disconnected from MQTT Broker")

# Callback khi một tin nhắn được gửi thành công
def on_publish(client, userdata, mid):
    print("Message published.")

def on_message(client, userdata, msg):
    print(msg.topic + " " + str(msg.payload))
    message = json.loads(msg.payload.decode())
    if msg.topic == MQTT_GATEWAY_LINKING:
        print("From topic " + MQTT_GATEWAY_LINKING)
        gatewayLinking(message)
    elif msg.topic == MQTT_TOPIC_CONNECT_KEY:
        print("From topic " + MQTT_TOPIC_CONNECT_KEY)
        connectKey(message)
    elif msg.topic == MQTT_TOPIC_KEEPALIVE:
        print("From topic " + MQTT_TOPIC_KEEPALIVE)
        send_keepalive(message)
    elif msg.topic == MQTT_SENSOR_SEND_NODE_INFO:
        print("From topic " + MQTT_SENSOR_SEND_NODE_INFO)
        addSensorNode(message)
    elif msg.topic == MQTT_ENERGY_SEND_NODE_INFO:
        print("From topic " + MQTT_ENERGY_SEND_NODE_INFO)
        addEnergyNode(message)
    elif msg.topic == MQTT_FAN_NODE_SEND_NODE_INFO:
        print("From topic " + MQTT_FAN_NODE_SEND_NODE_INFO)
        addFanNode(message)
    elif msg.topic == MQTT_AC_SEND_NODE_INFO:
        print("From topic " + MQTT_AC_SEND_NODE_INFO)
        addACNode(message)
    elif msg.topic == MQTT_SEND_ENV_PARAMS:
        print("From topic " + MQTT_SEND_ENV_PARAMS)
        setEnvPmv(message)
    elif msg.topic == MQTT_TOPIC_CONTROL_FAN:
        print("From topic " + MQTT_TOPIC_CONTROL_FAN)
        controlFan(message)
    elif msg.topic == MQTT_TOPIC_CONTROL_AC:
        print("From topic " + MQTT_TOPIC_CONTROL_AC)
        controlAC(message)

# Hàm kết nối tới MQTT Broker và gửi dữ liệu
def publish_to_mqtt(data, topic):
    message = None
    if topic == MQTT_TOPIC_SENSOR_DATA:
        message = {
            "operator": "send_pmv_data",
            "status": 1,
            "info": {
                "mac": MAC,
                "temp": data[0],
                "humid": data[1],
                "wind": data[2],
                "pm25": data[3],
                "sensor_id": data[5],
            }
        }
    elif topic == MQTT_TOPIC_EM_DATA:
        message = {
            "operator": "send_em_data",
            "status": 1,
            "info": {
                "mac": MAC,
                "voltage": data[0],
                "current": data[1],
                "frequency": data[2],
                "active_power": data[3],
                "power_factor": data[4],
                "em_id": data[5],
            }
        }
    elif topic == MQTT_TOPIC_FAN_DATA:
        message = {
            "operator": "send_fan_data",
            "status": 1,
            "info": {
                "mac": MAC,
                "set_speed": data[0],
                "control_mode": data[1],
                "set_time": data[2],
                "fan_id": data[4],
            }
        }
    elif topic == MQTT_TOPIC_AC_DATA:
        message = {
            "operator": "send_ac_data",
            "status": 1,
            "info": {
                "mac": MAC,
                "set_temp": data[0],
                "state": data[1],
                "control_mode": data[2],
                "ac_id": data[4],
            }
        }
    pub_message = json.dumps(message)
    result = client.publish(topic, pub_message)
    if result.rc == mqtt.MQTT_ERR_SUCCESS:
        print(f"Published to {topic}: {message}")
    else:
        print(f"Failed to publish to {topic}")

def save_sensor_data(data):
    db = create_connection()
    if db is None:
        print("Unable to connect to database")
        return
    
    cursor = db.cursor()
    current_timestamp = time.time()
    query = "UPDATE SensorNode SET temp = %s, humid = %s, wind = %s, pm25 = %s, time = %s WHERE sensor_id = %s"
    cursor.execute(query, (data['temp'], data['humid'], data['wind'], data['pm25'], current_timestamp, data['sensor_id'],))
    db.commit()
    print(f"Saved sensor data: {data}")
    cursor.close()
    db.close()

# Function to save fan data to MySQL database
def save_fan_data(data):
    db = create_connection()
    if db is None:
        print("Unable to connect to database")
        return
    
    cursor = db.cursor()
    current_timestamp = time.time()
    query = "UPDATE Fan SET set_speed = %s, control_mode = %s, set_time = %s, time = %s WHERE fan_id = %s"
    cursor.execute(query, (data['set_speed'], data['control_mode'], data['set_time'], current_timestamp, data['fan_id']))
    db.commit()
    print(f"Saved fan data: {data}")
    cursor.close()
    db.close()

# Function to save energy measure data to MySQL database
def save_em_data(data):
    db = create_connection()
    if db is None:
        print("Unable to connect to database")
        return
    
    cursor = db.cursor()
    current_timestamp = time.time()
    query = "UPDATE EnergyMeasure SET voltage = %s, current = %s, active_power = %s, power_factor = %s, frequency = %s, time = %s WHERE em_id = %s"
    cursor.execute(query, (data['voltage'], data['current'], data['active_power'], data['power_factor'], data['frequency'], current_timestamp, data['em_id'],))
    db.commit()
    print(f"Saved EM data: {data}")
    cursor.close()
    db.close()

# Function to save air conditioner data to MySQL database
def save_ac_data(data):
    db = create_connection()
    if db is None:
        print("Unable to connect to database")
        return
    
    cursor = db.cursor()
    current_timestamp = time.time()
    query = "UPDATE AirConditioner SET set_temp = %s, state = %s, control_mode = %s, time = %s WHERE ac_id = %s"
    cursor.execute(query,(data['set_temp'],data['state'], data['control_mode'], current_timestamp, data['ac_id']))
    db.commit()
    print(f"Saved AC data: {data}")
    cursor.close()
    db.close()

# Hàm gửi keepalive
def send_keepalive(message):
    status = message["status"]
    if status == 1:
        keepalive_message = {
            "operator": "keepalive_ack",
            "status": 1,
            "info": {
                "mac": MAC
            }
        }
        publish_to_mqtt(MQTT_TOPIC_KEEPALIVE_ACK, keepalive_message)

def gatewayLinking(message):
    mac = message["info"]["mac"]
    allowed = message["info"]["allowed"]
    if mac == MAC and allowed == 1:
        # client subscribe all
        client.subscribe(MQTT_TOPIC_CONNECT_KEY)
        client.subscribe(MQTT_TOPIC_KEEPALIVE)
        client.subscribe(MQTT_SENSOR_SEND_NODE_INFO)
        client.subscribe(MQTT_ENERGY_SEND_NODE_INFO)
        client.subscribe(MQTT_FAN_NODE_SEND_NODE_INFO)
        client.subscribe(MQTT_AC_SEND_NODE_INFO)
        client.subscribe(MQTT_SEND_ENV_PARAMS)
        client.subscribe(MQTT_TOPIC_CONTROL_FAN)
        client.subscribe(MQTT_TOPIC_CONTROL_AC)
        print("Gateway has connected to server")
    elif allowed == 0:
        print("Access to database failed")
    else:
        print("Undefined message")

def connectKey(message):
    # mac = message["info"]["mac"]
    # type_node = message["info"]["type_node"]
    # connect_key = message["info"]["connect_key"]
    
    # if mac == MAC:
    #     # open BLE network for node
    pass

def addSensorNode(client, message):
    status = message["status"]
    mac = message["info"]["mac"]
    if status == 1 and mac == MAC:
        sensor_id = message["info"]["sensor_id"]

        db = create_connection()
        if db is None:
            print("Unable to connect to database")
            return

        cursor = db.cursor()
        query = "INSERT INTO RegistrationSensor (id) VALUES ('%s')"
        cursor.execute(query, (sensor_id,))
        db.commit()
        cursor.close()
        db.close()

        mqtt_pub_message = {
            'operator': 'add_sensor_node_ack',
            'status': 1
        }
        client.publish(MQTT_SENSOR_SEND_NODE_INFO_ACK, json.dumps(mqtt_pub_message))

def addEnergyNode(message):
    status = message["status"]
    mac = message["info"]["mac"]
    if status == 1 and mac == MAC:
        id = message["info"]["id"]

        db = create_connection()
        if db is None:
            print("Unable to connect to database")
            return

        cursor = db.cursor()
        query = "INSERT INTO RegistrationEnergy (id) VALUES ('%s')"
        cursor.execute(query, (id,))
        db.commit()
        cursor.close()
        db.close()

        mqtt_pub_message = {
            'operator': 'add_em_node_ack',
            'status': 1
        }
        client.publish(MQTT_ENERGY_SEND_NODE_INFO_ACK, json.dumps(mqtt_pub_message))

def addFanNode(message):
    status = message["status"]
    mac = message["info"]["mac"]
    if status == 1 and mac == MAC:
        id = message["info"]["id"]

        db = create_connection()
        if db is None:
            print("Unable to connect to database")
            return

        cursor = db.cursor()
        query = "INSERT INTO RegistrationFan (id, model, sensor_link) VALUES ('%s', 'pmv_model', 'None')"
        cursor.execute(query, (id,))
        db.commit()
        cursor.close()
        db.close()

        mqtt_pub_message = {
            'operator': 'add_fan_node_ack',
            'status': 1
        }
        client.publish(MQTT_FAN_SEND_NODE_INFO_ACK, json.dumps(mqtt_pub_message))

def addACNode(message):
    status = message["status"]
    mac = message["info"]["mac"]
    if status == 1 and mac == MAC:
        id = message["info"]["id"]

        db = create_connection()
        if db is None:
            print("Unable to connect to database")
            return

        cursor = db.cursor()
        query = "INSERT INTO RegistrationAC (id, model, sensor_link) VALUES ('%s', 'pmv_model', 'None')"
        cursor.execute(query, (id,))
        db.commit()
        cursor.close()
        db.close()

        mqtt_pub_message = {
            'operator': 'add_ac_node_ack',
            'status': 1
        }
        client.publish(MQTT_AC_SEND_NODE_INFO_ACK, json.dumps(mqtt_pub_message))


def setEnvPmv(message):
    status = message["status"]
    mac = message["info"]["mac"]
    if status == 1 and mac == MAC:
        met = message["info"]["met"]
        clo = message["info"]["clo"]
        pmv_ref = message["info"]["pmv_ref"]

        db = create_connection()
        if db is None:
            print("Unable to connect to database")
            return

        cursor = db.cursor()
        query = "INSERT INTO PMVtable (met, clo, pmv_ref, outdoor_temp) VALUES (%s, %s, %s, %s)"
        cursor.execute(query, (met, clo, pmv_ref, 29)) # hard code outdoor temp = 29
        db.commit()
        cursor.close()
        db.close()

def controlFan(message):
    status = message["status"]
    if status == 1:
        print(message)
        control_mode = message["info"]["control_mode"]
        global_var.fan_id_target = message["info"]["fan_id"]
        global_var.set_speed_target = message["info"]["set_speed"]
        data = message["info"]
        save_fan_data(data)
        if control_mode == 0:
            fan_control_signal = True
            with open("myfile.pickle", "wb") as outfile:
                pickle.dump(fan_control_signal, outfile)
            # global_var.set_fan_control_signal(True)

def controlAC(message):
    print(message)
    status = message["status"]
    if status == 1:
        control_mode = message["info"]["control_mode"]
        global_var.ac_id_target = message["info"]["ac_id"]
        global_var.set_temp_target = message["info"]["set_temp"]
        global_var.state_target = message["info"]["state"]
        data = message["info"]
        save_ac_data(data)
        if control_mode == 0:
            # global_var.ac_control_signal = True
            ac_control_signal = True
            with open("myfile.pickle", "wb") as outfile:
                pickle.dump(ac_control_signal, outfile)
            # global_var.set_ac_control_signal(True)

def sendData():
    while True:
    # Lấy dữ liệu từ các bảng MySQL
        pmv_data = fetch_data_from_mysql("SELECT * FROM PMVtable")
        sensor_data = fetch_data_from_mysql("SELECT * FROM SensorNode")
        fan_data = fetch_data_from_mysql("SELECT * FROM Fan")
        em_data = fetch_data_from_mysql("SELECT * FROM EnergyMeasure")
        ac_data = fetch_data_from_mysql("SELECT * FROM AirConditioner")

        # Gửi dữ liệu lên MQTT Broker với các topic tương ứng
        # if pmv_data:
        #     publish_to_mqtt((pmv_data), MQTT_TOPIC_PMV_DATA)

        if sensor_data:
            publish_to_mqtt((sensor_data), MQTT_TOPIC_SENSOR_DATA)

        if fan_data:
            publish_to_mqtt((fan_data), MQTT_TOPIC_FAN_DATA)

        if em_data:
            publish_to_mqtt((em_data), MQTT_TOPIC_EM_DATA)

        if ac_data:
            publish_to_mqtt((ac_data), MQTT_TOPIC_AC_DATA)

            # Gửi keepalive mỗi 30 phút (1800 giây)
            # send_keepalive()
        time.sleep(300)

def saveData():
    while True:
        if global_var.save_sensor_data_signal == True:
            save_sensor_data(global_var.sensor_data_global)
            global_var.save_sensor_data_signal = False
        if global_var.save_energy_data_signal == True:
            save_sensor_data(global_var.energy_data_global)
            global_var.save_energy_data_signal = False
        time.sleep(5)

client = connect_mqtt()
# auto connect when ON
gateway_pub_message = {
    "operator": "server_connect",
    "status": 1,
    "info": {
        "mac": MAC
    }
}

client.publish(MQTT_GATEWAY_REGISTRY, json.dumps(gateway_pub_message))
mqtt_thread = threading.Thread(target=run_mqtt_client)
mqtt_thread.start()

send_data_to_server = threading.Thread(target=sendData)
send_data_to_server.start()
