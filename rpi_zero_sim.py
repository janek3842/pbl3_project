import time
import paho.mqtt.client as mqtt
import json
import random

BROKER = "localhost"

# Dane przypisane na stale
RESPONSE_TOPIC = "published_data/A/sensor-01"
LISTEN_ON_TOPIC = "A"
SENSOR = "sensor-01"
ADDRESS = 0x76

MEAS_NUM = 5 # liczba pomiarow przed wyslaniem wynikow
MEAS_TIME = 1 # czas pojedycznego pomiaru

def measure_params():
    """Wykonuje pomiar wszystkich parametrow"""
    try:
        temperature = random.randint(15,25)
        humidity = random.randint(0,10)
        smoke_level = random.randint(2,7)
    except Exception as e:
        print(f"Blad odczytu z czujnika {e}")

    return temperature, humidity, smoke_level

def on_message(client, userdata, msg):
    """Obsluga wiadomosci od Rpi 4"""
    try:
        topic = msg.topic
        payload = msg.payload.decode()
        print(f"Odebrano zadanie od Rpi 4 z tematu {topic}: {payload}")

        """Utworzenie pustych list majacych na celu przechowywanie wynikow pomiarow
        w celu ich usrednienia i wyslania do Rpi 4"""
        temp = []
        hum = []
        smk = []
        for _ in range(MEAS_NUM):
            temperature, humidity, smoke_level = measure_params()
            temp.append(temperature)
            hum.append(humidity)
            smk.append(smoke_level)
            time.sleep(MEAS_TIME)

        avg_temp = round(sum(temp)/len(temp), 2)
        avg_hum = round(sum(hum)/len(hum), 2)
        avg_smk = round(sum(smk)/len(smk), 2)

        message = {
            "temperature": avg_temp,
            "humidity": avg_hum,
            "smoke_level": avg_smk,
            "id": SENSOR
        }

        message_json = json.dumps(message)
        client.publish(RESPONSE_TOPIC, message_json)
        print(f"Opublikowano dane na temat {RESPONSE_TOPIC}: {message_json}")

    except Exception as e:
        print(f"Błąd odczytu z czujnika: {e}")

def main():
    client = mqtt.Client()
    client.on_message = on_message

    try:
        client.connect(BROKER, 1883, 60)
        client.subscribe(LISTEN_ON_TOPIC)
        client.loop_forever()

    except KeyboardInterrupt:
        print('Program zatrzymany')
    except Exception as e:
        print('Wystąpił błąd:', str(e))
    finally:
        client.disconnect()

if __name__ == '__main__':
    main()