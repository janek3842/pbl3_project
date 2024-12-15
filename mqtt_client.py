import paho.mqtt.client as mqtt
import json
import time

def merge_topic(section=None):
    """Tworzy temat subskrypcji dla danej sekcji"""
    if section:
        return f"{section}/#"
    return "#"


def on_message(client, userdata, msg):
    """Funkcja do obslugi odebranych danych"""
    try:
        topic = msg.topic
        payload = msg.payload.decode()  # Dekodowanie wiadomosci
        print(f"Received message for topic {topic}: {payload}")

        data = json.loads(payload)  # Parsowanie JSON
        sensor_id = data["id"]

        # Zapis danych do userdata
        if userdata is not None:
            userdata[sensor_id] = data  # Przechowujemy dane w slowniku
            print(f"Data saved for device {sensor_id}: {data}")
        else:
            print("Couldn't initialize userdata")
    except Exception as e:
        print(f"Error while receiving data: {e}")


def setup_mqtt_client():
    """Konfiguracja klienta MQTT"""
    client = mqtt.Client()
    client.on_message = on_message

    # Inicjalizacja userdata jako pustego slownika
    client.user_data_set({})
    return client


def collect_sensor_data(client, section, timeout=10):
    """Nasluchuje odpowiedzi z czujnikow w danej sekcji"""
    listen_on_topic = "published_data/" + merge_topic(section)
    client.subscribe(listen_on_topic, qos=2)
    print(f"Subscribing topic: {listen_on_topic}")

    # Oczekiwanie na odpowiedzi
    start_time = time.time()
    while time.time() - start_time < timeout:
        client.loop(timeout=1.0)  # Przetwarzanie zdarzen MQTT

    # Pobranie danych z userdata
    sensor_data = client._userdata
    if sensor_data:
        print("Collected data from sensors:")
        for sensor_id, data in sensor_data.items():
            print(f"Device {sensor_id}: {data}")
    else:
        print("No data from sensors")

    return sensor_data  # Zwracamy dane do dalszego uďż˝ycia


def send_request(client, section):
    """Publikuje zadanie na temat danej sekcji"""
    request_topic = section
    client.publish(request_topic, qos=2)
    print(f"Requested measurements from topic: {request_topic}")

def mqtt_get_measurements(broker, room_id):
    """Function for getting measurements"""
    client = setup_mqtt_client()
    try:
        # Connect to client
        client.connect(broker, 1883, 60)
        # Whole procedure for getting data from all sensor devices
        send_request(client, room_id)
        sensor_data = collect_sensor_data(client, room_id)
        return sensor_data
    except KeyboardInterrupt:
        print("Zatrzymano program")
    finally:
        client.disconnect()
