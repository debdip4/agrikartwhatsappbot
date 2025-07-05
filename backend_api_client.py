import requests
import logging
from config import BACKEND_API_BASE_URL

def check_farmer_exists(phone_number):
    """Checks if a farmer is already registered."""
    url = f"{BACKEND_API_BASE_URL}/api/v1/farmer/check/{phone_number}/"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return True
        return False
    except requests.exceptions.RequestException as e:
        logging.error(f"Error checking farmer existence: {e}")
        return False

def register_farmer(details):
    """Registers a new farmer."""
    url = f"{BACKEND_API_BASE_URL}/api/v1/auth/signup/farmer/"
    try:
        response = requests.post(url, json=details)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error registering farmer: {e}")
        logging.error(f"Response: {e.response.text if e.response else 'N/A'}")
        return None

def login_farmer(phone_number, password):
    """Logs in a farmer to get an auth token."""
    url = f"{BACKEND_API_BASE_URL}/api/v1/auth/token/"
    data = {"phone": phone_number, "password": password}
    try:
        response = requests.post(url, json=data)
        if response.status_code == 200:
            return response.json().get("access")
        return None
    except requests.exceptions.RequestException as e:
        logging.error(f"Error logging in farmer: {e}")
        return None

def add_produce(token, produce_details):
    """Adds a new produce listing for a farmer."""
    url = f"{BACKEND_API_BASE_URL}/api/v1/produce/"
    headers = {"Authorization": f"Bearer {token}"}
    data = {
        "name": produce_details["name"],
        "price": float(produce_details["price_per_kg"]),
        "quantity": float(produce_details["quantity_kg"]),
        "category": produce_details.get("category", "Others"),
    }
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error adding produce: {e}")
        logging.error(f"Response: {e.response.text if e.response else 'N/A'}")
        return None
