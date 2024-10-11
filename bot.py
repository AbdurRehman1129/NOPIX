import requests
import json
import time
import random
from setproctitle import setproctitle
from models import get_image_data  # Adjusted to import from models
from colorama import Fore, Style, init
from datetime import datetime, timedelta
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import urllib.parse  # For decoding the URL-encoded initData

# API configuration
url = "https://notpx.app/api/v1"

# Constants
WAIT = 180 * 3
DELAY = 1
WIDTH = 1000
HEIGHT = 1000
MAX_HEIGHT = 50

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

# Create a session with retry logic
session = get_session_with_retries()

# Function to get the color of a pixel from the server using query ID
def get_color(pixel, query_id):
    try:
        response = session.get(f"{url}/image/get/{str(pixel)}?query_id={query_id}", timeout=10)
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
def claim(query_id):
    log_message("Claiming resources", Fore.CYAN)
    try:
        session.get(f"{url}/mining/claim?query_id={query_id}", timeout=10)
    except requests.exceptions.RequestException as e:
        log_message(f"Failed to claim resources: {e}", Fore.RED)

# Function to calculate pixel index based on x, y position
def get_pixel(x, y):
    return y * 1000 + x + 1

# Function to get x, y position from pixel index
def get_pos(pixel, size_x):
    return pixel % size_x, pixel // size_x

# Function to get pixel index based on canvas position
def get_canvas_pos(x, y, start_x, start_y):
    return get_pixel(start_x + x - 1, start_y + y - 1)

# Function to perform the painting action
def paint(canvas_pos, color, query_id):
    data = {
        "pixelId": canvas_pos,
        "newColor": color
    }

    try:
        response = session.post(f"{url}/repaint/start?query_id={query_id}", data=json.dumps(data), timeout=10)
        x, y = get_pos(canvas_pos, 1000)

        if response.status_code == 400:
            log_message("Out of energy", Fore.RED)
            return False
        if response.status_code == 401:
            return -1

        log_message(f"Paint: {x},{y}", Fore.GREEN)
        return True
    except requests.exceptions.RequestException as e:
        log_message(f"Failed to paint: {e}", Fore.RED)
        return False

# Function to extract the username from the URL-encoded init data
def extract_username_from_initdata(init_data):
    # URL decode the init data
    decoded_data = urllib.parse.unquote(init_data)
    
    # Find the part that contains "username"
    username_start = decoded_data.find('"username":"') + len('"username":"')
    username_end = decoded_data.find('"', username_start)
    
    if username_start != -1 and username_end != -1:
        return decoded_data[username_start:username_end]
    
    return "Unknown"

# Function to load accounts from data.txt
def load_accounts_from_file(filename):
    with open(filename, 'r') as file:
        accounts = [line.strip() for line in file if line.strip()]
    return accounts

# Main function to perform the painting process
def main(auth, account):
    headers = {'authorization': auth}
    query_id = "YOUR_QUERY_ID"  # Replace with your actual Query ID

    try:
        # Claim resources
        claim(query_id)

        size = len(get_image_data()) * len(get_image_data()[0])
        order = [i for i in range(size)]
        random.shuffle(order)

        for pos_image in order:
            x, y = get_pos(pos_image, len(get_image_data()[0]))
            time.sleep(0.05 + random.uniform(0.01, 0.1))
            try:
                color = get_color(get_canvas_pos(x, y, start_x, start_y), query_id)
                if color == -1:
                    log_message("DEAD :(", Fore.RED)
                    print(headers["authorization"])
                    break

                if get_image_data()[y][x] == ' ' or color == c[get_image_data()[y][x]]:
                    log_message(f"Skip: {start_x + x - 1},{start_y + y - 1}", Fore.RED)
                    continue

                result = paint(get_canvas_pos(x, y, start_x, start_y), c[get_image_data()[y][x]], query_id)
                if result == -1:
                    log_message("DEAD :(", Fore.RED)
                    print(headers["authorization"])
                    break
                elif result:
                    continue
                else:
                    break

            except IndexError:
                log_message(f"IndexError at pos_image: {pos_image}, y: {y}, x: {x}", Fore.RED)

    except requests.exceptions.RequestException as e:
        log_message(f"Network error in account {account}: {e}", Fore.RED)

# Main process loop to manage accounts and sleep logic
def process_accounts(accounts):
    # Track the start time of the first account
    first_account_start_time = datetime.now()

    for account in accounts:
        # Process each account one by one
        username = extract_username_from_initdata(account)
        log_message(f"--- STARTING SESSION FOR ACCOUNT: {username} ---", Fore.BLUE)
        main(account, account)

    # Calculate the time elapsed since the first account started processing
    time_elapsed = datetime.now() - first_account_start_time
    time_to_wait = timedelta(hours=1) - time_elapsed

    if time_to_wait.total_seconds() > 0:
        log_message(f"SLEEPING FOR {int(time_to_wait.total_seconds() // 60)} MINUTES", Fore.YELLOW)
        time.sleep(time_to_wait.total_seconds())
    else:
        log_message(f"NO SLEEP NEEDED, TOTAL PROCESSING TIME EXCEEDED 1 HOUR", Fore.YELLOW)

if __name__ == "__main__":
    # Load accounts from the data.txt file
    accounts = load_accounts_from_file('data.txt')

    # Infinite loop to process accounts
    while True:
        process_accounts(accounts)
