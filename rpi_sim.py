import http_client
from http_client import get_device_ids, get_limits

base_url = "http://13.60.19.183:1883"
room_id = 1

# Sensor class
class Sensor:
    class Attribute:
        def __init__(self, name, value, limit):
            self.name = name
            self.value = value
            self.limit = limit

        def is_exceeded(self):
            return self.value > self.limit

        def is_close(self):
            return self.value > (0,75 * self.limit)

        def __str__(self):
            return f"{self.name}, value: {self.value}, limit: {self.limit}, is close?: {self.is_close()}, is exceeded?: {self.is_exceeded()}"

    def __init__(self, sensor_id):
        # Setting given sensor id
        self.id = sensor_id
        # Setting some default values
        self.temp = self.Attribute("temperature", 15, 30)
        self.hum = self.Attribute("humidity", 20, 50)
        self.smoke = self.Attribute("smoke_level", 5, 15)

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

    def __str__(self):
        return f"sensor {self.id}\n {self.temp}\n {self.hum}\n {self.smoke}\n is exceeded? {self.is_exceeded()}"

# Function for checking changes in the sensors on the server and adding/deleting devices
def update_sensor_list(sensors):
    # Creating list of sensor ids
    sensor_ids = [sensor.id for sensor in sensors]
    # Retrieving device list from server
    data = get_device_ids(base_url, room_id)
    # Creating a list of all device ids from the received json
    updated_sensor_ids = []
    for entry in data:
        for key, value in entry.items():
            if key == "device_id":
                updated_sensor_ids.append(value)

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

# Function for updating sensor limits based on server data
def update_sensor_limits(sensors):
    # Updating limits for every sensor
    for sensor in sensors:
        limits_json = get_limits(base_url, room_id, sensor.id)
        sensor.update_all_limits(limits_json)
    # Return updated sensor list
    return sensors

# Function for updating sensor values from the given value (hujowa trzeba zmienic)
def update_sensor_values(sensors, values_json):
    for sensor in sensors:
        sensor.update_all_values(values_json)
    # Return updated sensor list
    return sensors

# Function returning the
def limit_control(sensors):
    return


sensors = []
sensors.append(Sensor(1))
sensors.append(Sensor(2))
sensors.append(Sensor(3))
for sensor in sensors:
    print(sensor)

sensors = update_sensor_list(sensors)
print("updated list")

for sensor in sensors:
    print(sensor)