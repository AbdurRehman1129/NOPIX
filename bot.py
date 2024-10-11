import requests
import json
import time
import random
from setproctitle import setproctitle
from models import get_image_data
from colorama import Fore, Style, init
from datetime import datetime, timedelta
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

url = "https://notpx.app/api/v1"

# Initialize colorama for colored output
init(autoreset=True)
setproctitle("notpixel")

# Define colors for pixel representation
c = {
    '#': "#000000",
    '.': "#3690EA",
    '*': "#ffffff"
}

# Function to log messages with timestamp in light grey color
def log_message(message, color=Style.RESET_ALL):
    current_time = datetime.now().strftime("[%H:%M:%S]")
    print(f"{Fore.LIGHTBLACK_EX}{current_time}{Style.RESET_ALL} {color}{message}{Style.RESET_ALL}")

# Function to initialize a requests session with retry logic
def get_session_with_retries(retries=3, backoff_factor=0.3, status_forcelist=(500, 502, 504)):
    session = requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

# Function to get the color of a pixel from the server
def get_color(pixel, header):
    try:
        response = session.get(f"{url}/image/get/{str(pixel)}", headers=header, timeout=10)
        if response.status_code == 401:
            return -1
        return response.json()['pixel']['color']
    except KeyError:
        return "#000000"
    except requests.exceptions.Timeout:
        log_message("Request timed out", Fore.RED)
        return "#000000"
    except requests.exceptions.ConnectionError as e:
        log_message(f"Connection error: {e}", Fore.RED)
        return "#000000"
    except requests.exceptions.RequestException as e:
        log_message(f"Request failed: {e}", Fore.RED)
        return "#000000"

# Function to claim resources from the server
def claim(header):
    log_message("Claiming resources", Fore.CYAN)
    try:
        session.get(f"{url}/mining/claim", headers=header, timeout=10)
    except requests.exceptions.RequestException as e:
        log_message(f"Failed to claim resources: {e}", Fore.RED)

# Function to perform the painting action
def paint(canvas_pos, color, header):
    data = {
        "pixelId": canvas_pos,
        "newColor": color
    }

    try:
        response = session.post(f"{url}/repaint/start", data=json.dumps(data), headers=header, timeout=10)

        if response.status_code == 400:
            log_message("Out of energy", Fore.RED)
            return False
        if response.status_code == 401:
            return -1

        log_message(f"Painted: {canvas_pos} with color {color}", Fore.GREEN)
        return True
    except requests.exceptions.RequestException as e:
        log_message(f"Failed to paint: {e}", Fore.RED)
        return False

# Function to load Query IDs from data.txt
def load_query_ids(filename):
    with open(filename, 'r') as file:
        query_ids = [line.strip() for line in file if line.strip()]
    return query_ids

# Main function to perform the painting process
def main(query_id):
    headers = {'authorization': query_id}
    # Initialize the session
    global session
    session = get_session_with_retries()

    # Fetch image data
    image_data = get_image_data()

    try:
        # Claim resources
        claim(headers)

        for y in range(len(image_data)):
            for x in range(len(image_data[0])):
                color = c.get(image_data[y][x], "#000000")  # Default to black if not found
                canvas_pos = get_pixel(x, y)

                time.sleep(0.05 + random.uniform(0.01, 0.1))  # Adding random delay
                current_color = get_color(canvas_pos, headers)
                if current_color == -1:
                    log_message("DEAD :(", Fore.RED)
                    break

                if image_data[y][x] == ' ' or current_color == color:
                    log_message(f"Skipping: {x},{y}", Fore.RED)
                    continue

                result = paint(canvas_pos, color, headers)
                if result == -1:
                    log_message("DEAD :(", Fore.RED)
                    break

    except requests.exceptions.RequestException as e:
        log_message(f"Network error: {e}", Fore.RED)

if __name__ == "__main__":
    # Load Query IDs from the data.txt file
    query_ids = load_query_ids('data.txt')

    # Loop through each Query ID
    for query_id in query_ids:
        log_message(f"--- STARTING SESSION FOR QUERY ID: {query_id} ---", Fore.BLUE)
        main(query_id)
