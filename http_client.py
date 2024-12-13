import requests
import json

# Function for putting the temperature, humidity and smoke level
# measured by the given device in given room
def send_measurements(base_url, room_id, device_id, temp, hum, smoke):
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
    else:
        print(f"Failed to send data, response {response.json()}")

# Function for posting a photo taken in the given room by the given camera
def send_photo(base_url, room_id, camera_id, file_path):
    # Parsing destination url
    dest_url = base_url + "/rooms/" + str(room_id) + "/cameras/" + str(camera_id) + "/data"

    # Opening file
    with open(file_path, "rb") as file:
        # Sending request
        response = requests.post(dest_url, files={"file": file})

    # Checking response code
    if response.status_code == 200:
        print(f"Data sent successfully, response {response.json()}")
    else:
        print(f"Failed to send data, response {response.json()}")

# Function for getting info on limits
def get_limits(base_url, room_id, device_id):
    # Parsing destination url
    dest_url = base_url + "/rooms/" + str(room_id) + "/sensor-devices/" + str(device_id) + "/limits"

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

# Function for getting sensor device ids
def get_device_ids(base_url, room_id):
    dest_url = base_url + "/rooms/" + str(room_id) + "/sensor-devices"
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

# Function for getting camera ids
def get_camera_ids(base_url, room_id):
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