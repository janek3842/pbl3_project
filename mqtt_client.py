import paho.mqtt.client as mqtt
import json
import time
from rpi_sim import retry


def merge_topic(section=None):
    """Creating a subscription topic for MQTT messages"""
    if section:
        return f"{section}/#"
    return "#"


def on_message(client, userdata, msg):
    """Function for parsing received data"""
    try:
        topic = msg.topic
        # Decoding message
        payload = msg.payload.decode()
        print(f"Received message for topic {topic}: {payload}")

        # JSON parsing
        data = json.loads(payload)
        sensor_id = data["id"]

        # Saving data to userdata
        if userdata is not None:
            # Saving parts of data in the userdata dict
            userdata[sensor_id] = data
            print(f"Data saved for device {sensor_id}: {data}")
        else:
            print("Couldn't initialize userdata")
    except Exception as e:
        print(f"Error while receiving data: {e}")


@retry(max_attemps=3, delay=5)
def connect_to_broker(client, broker):
    client.connect(broker, 1883, 60)


def setup_mqtt_client():
    """MQTT client configuration"""
    client = mqtt.Client()
    client.on_message = on_message

    # Initializing userdata as a empty dict
    client.user_data_set({})
    return client


def collect_sensor_data(client, section, timeout=10):
    """Collecting data from sensors in given room"""
    listen_on_topic = "published_data/" + merge_topic(section)
    client.subscribe(listen_on_topic, qos=2)
    print(f"Subscribing topic: {listen_on_topic}")

    # Waiting for published messaged
    start_time = time.time()
    while time.time() - start_time < timeout:
        client.loop(timeout=1.0)

    # Accessing data from userdata
    sensor_data = client._userdata
    if sensor_data:
        print("Collected data from sensors:")
        for sensor_id, data in sensor_data.items():
            print(f"Device {sensor_id}: {data}")
    else:
        print("No data from sensors")
        return None
    # Returning sensor_data if received
    return sensor_data


@retry(max_attemps=3, delay=5)
def send_request(client, section):
    """Publikuje zadanie na temat danej sekcji"""
    request_topic = section
    client.publish(request_topic, qos=2)
    print(f"Requested measurements from topic: {request_topic}")


def mqtt_get_measurements(broker, room_id):
    """Function for getting measurements"""
    client = setup_mqtt_client()
    try:
        # Connect to broker
        connect_to_broker(client, broker)
        # Whole procedure for getting data from all sensor devices
        send_request(client, room_id)

        sensor_data = collect_sensor_data(client, room_id)
        if sensor_data is None:
            print("Didn't receive any data")
            return None
        else:
            return sensor_data
    except KeyboardInterrupt:
        print("Zatrzymano program")
    finally:
        client.disconnect()
