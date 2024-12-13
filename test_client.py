from csv import excel_tab

import paho.mqtt.client as mqtt
import logging

broker = 'rpimuseum15.local'
port = 1883
topic = ''
client_id = 1

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to broker")
    else:
        print("Connection failed, return code %d", rc)

FIRST_RECONNECT_DELAY = 1
RECONNECT_RATE = 2
MAX_RECONNECT_COUNT = 12
MAX_RECONNECT_DELAY = 60

def on_disconnect(client, userdata, rc):
    logging.info("Disconnected from broker with code %d", rc)
    reconnect_count, reconnect_delay = 0, FIRST_RECONNECT_DELAY
    while reconnect_count < MAX_RECONNECT_COUNT:
        logging.info("Reconnecting in %d seconds...", reconnect_delay)
        time.sleep(reconnect_delay)

        try:
            client.reconnect()
            return
        except Exception as err:
            logging.error("%s. Reconnect failed, retrying", err)

        reconnect_delay *= RECONNECT_RATE
        reconnect_count = min(reconnect_count, MAX_RECONNECT_DELAY)
        reconnect_count += 1
    logging.info("Reconnect failed after %d attempts.", reconnect_count)

