import requests
import json


def send_measurements(base_url, room_id, device_id, temp, hum, smoke):
    """Function for putting the temperature, humidity and smoke level
        measured by the given device in given room"""
    # Defining data and headers
    data = {
        "temperature": temp,
        "humidity": hum,
        "smoke_level": smoke
    }
    headers = {"Content-Type": "application/json"}

    # Parsing destination url
    dest_url = base_url + "/rooms/" + str(room_id) + "/sensor-devices/" + str(device_id) + "/data"

    # Sending request
    response = requests.put(dest_url, data=json.dumps(data), headers=headers)

    # Checking response code
    if response.status_code == 200:
        print(f"Data sent successfully, response {response.json()}")
        return
    else:
        print(f"Failed to send data, response {response.json()}")
        return

def send_photo(base_url, room_id, camera_id, file_path):
    """Function for posting a photo taken in the given room by the given camera"""
    # Parsing destination url
    dest_url = base_url + "/rooms/" + str(room_id) + "/cameras/" + str(camera_id) + "/images"

    try:
        # Opening file
        with open(file_path, "rb") as file:
            # Sending request
            response = requests.post(dest_url, files={"file": file})
    except Exception as e:
        print(f"Couldn't send photo, error: {e}")

    # Checking response code
    if response.status_code == 200:
        print(f"Data sent successfully, response {response.json()}")
        return
    else:
        print(f"Failed to send data, response {response.json()}")
        return

def get_limits(base_url, room_id):
    """Function for getting info on limits"""
    # Parsing destination url
    dest_url = base_url + "/rooms/" + str(room_id) + "/sensor-devices/limits"

    try:
        # Sending request
        response = requests.get(dest_url, timeout=10)
        response.raise_for_status()
        # Returning data if successfully received
        data = response.json()
        print(data)
        return data
    # Checking for exceptions
    except requests.exceptions.RequestException as e:
        print(f"Failed to get limits, response {e}")
        return None
    except ValueError:
        print("Can't process the response as JSON")
        return None

def get_people_number(base_url, room_id, camera_id):
    """Function for getting people number limit"""
    dest_url = base_url + "/rooms/" + str(room_id) + "/cameras/" + str(camera_id) + "/people-num"
    try:
        # Sending request
        response = requests.get(dest_url, timeout=10)
        response.raise_for_status()
        # Returning data if successfully received
        data = response.json()
        print(data)
        return data["data"]["people_num"]
    # Checking for exceptions
    except requests.exceptions.RequestException as e:
        print(f"Failed to get people number, response {e}")
        return None
    except ValueError:
        print("Can't process the response")
        return None

def get_device_ids(base_url, room_id):
    """Function for getting sensor device ids"""
    dest_url = base_url + "/rooms/" + str(room_id) + "/sensor-devices"
    try:
        # Sending request
        response = requests.get(dest_url, timeout=10)
        response.raise_for_status()
        # Returning data if successfully received
        data = response.json()
        print(data)
        return data
    # Checking for exceptions
    except requests.exceptions.RequestException as e:
        print(f"Failed to get limits, response {e}")
        return None
    except ValueError:
        print("Can't process the response as JSON")
        return None

def get_camera_ids(base_url, room_id):
    """Function for getting camera ids"""
    dest_url = base_url + "/rooms/" + str(room_id) + "/cameras"
    try:
        # Sending request
        response = requests.get(dest_url, timeout=10)
        response.raise_for_status()
        # Returning data if successfully received
        data = response.json()
        return data
    # Checking for exceptions
    except requests.exceptions.RequestException as e:
        print(f"Failed to get limits, response {e}")
        return None
    except ValueError:
        print("Can't process the response as JSON")
        return None