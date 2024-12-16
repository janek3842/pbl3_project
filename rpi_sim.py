from http_client import get_device_ids, get_limits, send_photo, send_measurements, get_people_number
import cv2
from mqtt_client import mqtt_get_measurements
import time
from functools import wraps

# Predefined room and camera id's
ROOM_ID = "A"
CAMERA_ID = "cam-03" # placeholders

# Defining seconds between measurements based on the state (0 - normal, 1 - warning, 2 - limits exceeded)
WAIT_TIMES = [60, 30, 20]

# Base url of the server
BASE_URL = "http://13.60.171.70:1880"

# MQTT broker
BROKER = "localhost"


class Sensor:
    """Class for storing the attributes of the sensor"""
    class Attribute:
        def __init__(self, name, value, limit):
            self.name = name
            self.value = value
            self.limit = limit

        def is_exceeded(self):
            return self.value > self.limit

        def is_close(self):
            return self.value > (0.75 * self.limit)

        def __str__(self):
            return f"{self.name}, value: {self.value}, limit: {self.limit}, is close?: {self.is_close()}, is exceeded?: {self.is_exceeded()}"

    def __init__(self, sensor_id):
        # Setting given sensor id
        self.id = sensor_id
        # Setting some default values
        self.temp = self.Attribute("temperature", 15, 30)
        self.hum = self.Attribute("humidity", 20, 50)
        self.smoke = self.Attribute("smoke_level", 5, 15)
        self.device_state = False

    def update_all_values(self, values_json):
        self.temp.value = values_json["temperature"]
        self.hum.value = values_json["humidity"]
        self.smoke.value = values_json["smoke_level"]

    def update_all_limits(self, limits_json):
        self.temp.limit = limits_json["temperature"]
        self.hum.limit = limits_json["humidity"]
        self.smoke.limit = limits_json["smoke_level"]

    def is_exceeded(self):
        return self.temp.is_exceeded() or self.hum.is_exceeded() or self.smoke.is_exceeded()

    def is_close(self):
        return self.temp.is_close() or self.hum.is_close() or self.smoke.is_close()

    def __str__(self):
        return f"sensor {self.id}\n {self.temp}\n {self.hum}\n {self.smoke}\n is exceeded? {self.is_exceeded()}"


class People:
    """Class for storing the number and limit of people"""
    def __init__(self):
        self.num = 0
        self.limit = 10

    def is_close(self):
        return self.num > (0.75 * self.limit)

    def is_exceeded(self):
        return self.num > self.limit


def retry(max_attemps, delay):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attemps = 0
            while attemps < max_attemps:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    attemps += 1
                    print(f"Attempt no. {attemps} failed: {e}, retrying")
                    time.sleep(delay)
            print(f"All {max_attemps} attemps failed")
            return None
        return wrapper
    return decorator


def update_sensor_list(sensors):
    """Function for checking changes in the sensors on the server and adding/deleting devices"""
    try:
        # Creating list of sensor ids
        sensor_ids = [sensor.id for sensor in sensors]
        # Retrieving device list from server
        data = get_device_ids(BASE_URL, ROOM_ID)
        # Creating a list of all device ids from the received json
        updated_sensor_ids = []
        devices = data["sensor_devices"]
        for device in devices:
            updated_sensor_ids.append(device["device_id"])

        # Determining added and deleted sensors
        sensor_ids_set = set(sensor_ids)
        updated_sensor_ids_set = set(updated_sensor_ids)
        deleted_sensor_ids = sensor_ids_set - updated_sensor_ids_set
        added_sensor_ids = updated_sensor_ids_set - sensor_ids_set

        # Updating sensor list
        updated_sensors = [sensor for sensor in sensors if sensor.id not in deleted_sensor_ids]
        for new_sensor_id in added_sensor_ids:
            updated_sensors.append(Sensor(new_sensor_id))
        # Returning the updated list
        return updated_sensors
    except Exception as e:
        print(f"Couldn't update sensor values, error: {e}, returning old values")
        return None


def update_sensor_limits(sensors):
    """Function for updating sensor limits based on server data"""
    # Updating limits for every sensor
    limits_json = get_limits(BASE_URL, ROOM_ID)
    if limits_json is None:
        print("Couldn't access the limit values")
        return None
    try:
        for sensor in sensors:
            sensor.update_all_limits(limits_json)
        ppl_limit = limits_json["people_num"]
        # Return updated sensor list
        return sensors, ppl_limit
    except Exception as e:
        print(f"Couldn't update sensor limits, error: {e}, returned old limits")
        return None


def update_sensor_values(sensors, values_json):
    """Function for updating sensor values from the given value"""
    try:
        print(values_json)
        for sensor in sensors:
            if sensor.id not in values_json:
                print(f"No data from device {sensor.id}")
            else:
                try:
                    sensor.update_all_values(values_json[sensor.id])
                    sensor.device_state = True
                    send_measurements(BASE_URL, ROOM_ID, sensor.id, sensor.temp.value, sensor.hum.value, sensor.smoke.value)
                except Exception as e:
                    print(f"Couldn't update {sensor.id} data, error {e}")
                    sensor.device_state = False
    except Exception as e:
        print(f"Couldn't update sensor values, error: {e}, returned old values")
        return None
    # Return updated sensor list
    return sensors


def limit_control(sensors, people):
    """Function controlling the exceeding of limits in the room (0 - good, 1 - warning, 2 - limits exceeded)"""
    warning = False
    # Checking if people number limits exceeded
    if people.is_exceeded():
        return 2
    elif people.is_close():
        warning = True
    # Checking if sensors measurement limits exceeded
    for sensor in sensors:
        if sensor.is_close():
            if not sensor.is_exceeded():
                warning = True
            else:
                return 2
    # Returning the state of values/limits in the room
    if warning:
        return 1
    else:
        return 0


def photo_capture(camera_id):
    """Function for capturing image from rpi camera"""
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: could not open camera")
        return None
    else:
        ret, frame = cap.read()
        if ret:
            cv2.imwrite(camera_id+".jpg", frame)
        else:
            print("Error: failed to capture image")
            return None
        cap.release()
        return


def photo_update(camera_id):
    """Function taking photo from camera and sending it to the server"""
    try:
        photo_capture(camera_id)
        send_photo(BASE_URL, ROOM_ID, camera_id, camera_id+".jpg")
        return
    except Exception as e:
        print(f"Couldn't update photo, error: {e}")
        return None


def sensors_info(sensors):
    """Debugginf function for printing out sensor info"""
    for sensor in sensors:
        print(sensor)


def main():
    sensors = []
    ppl = People()

    while True:
        # Get data from mqtt devices
        meas_json = mqtt_get_measurements(BROKER, ROOM_ID)

        # Check for changes in sensor list coming from the website
        sensors = update_sensor_list(sensors) or sensors

        # Update sensor limits from website
        sensors, ppl.limit = update_sensor_limits(sensors) or sensors, ppl.limit

        # If didn't receive sensor measurements, don't update values on server
        if meas_json is None:
            print("Error receiving data from sensors, can't update values on server")
        else:
            # Update previously measured sensor values and sending them to the server and database
            sensors = update_sensor_values(sensors, meas_json) or sensors

        # Take and update photo
        photo_update(CAMERA_ID)

        # Get people number from server
        ppl.num = get_people_number(BASE_URL, ROOM_ID, CAMERA_ID) or ppl.num

        # Print all sensor info (for testing)
        sensors_info(sensors)

        # Printing door state to simulate the LED/gate
        door_state = limit_control(sensors, ppl)
        print(f"door state: {door_state}")

        # Wait before the next measurements
        time.sleep(WAIT_TIMES[door_state])


if __name__ == "__main__":
    main()
