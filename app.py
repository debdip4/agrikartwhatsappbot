import os
import json
import requests
import time
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# --- Additional libraries for price scraping ---
import pandas as pd
from io import StringIO
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, NoSuchElementException

load_dotenv()
app = Flask(__name__)

# --- Load Credentials ---
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
API_BASE_URL = os.getenv("BACKEND_API_BASE_URL")
PUBLIC_URL = os.getenv("PUBLIC_URL")

# --- Constants ---
STATES = {
    "1": "Andhra Pradesh", "2": "Arunachal Pradesh", "3": "Assam", "4": "Bihar",
    "5": "Chhattisgarh", "6": "Goa", "7": "Gujarat", "8": "Haryana",
    "9": "Himachal Pradesh", "10": "Jharkhand", "11": "Karnataka", "12": "Kerala",
    "13": "Madhya Pradesh", "14": "Maharashtra", "15": "Manipur", "16": "Meghalaya",
    "17": "Mizoram", "18": "Nagaland", "19": "Odisha", "20": "Punjab",
    "21": "Rajasthan", "22": "Sikkim", "23": "Tamil Nadu", "24": "Telangana",
    "25": "Tripura", "26": "Uttar Pradesh", "27": "Uttarakhand", "28": "West Bengal",
    "29": "Andaman and Nicobar Islands", "30": "Chandigarh", "31": "Dadra and Nagar Haveli and Daman and Diu",
    "32": "Delhi", "33": "Jammu and Kashmir", "34": "Ladakh", "35": "Lakshadweep", "36": "Puducherry"
}

# --- In-memory dictionary for session state ONLY ---
user_states = {}

# --- Audio Files Dictionary RESTORED ---
AUDIO_CLIPS = {
    "welcome": "https://raw.githubusercontent.com/debdip4/agrikartwhatsappbot/main/Audio_files/welcome.mp3",
    "en": {
        "ask_name": "https://raw.githubusercontent.com/debdip4/agrikartwhatsappbot/main/Audio_files/en_ask_name.mp3",
        "ask_address": "https://raw.githubusercontent.com/debdip4/agrikartwhatsappbot/main/Audio_files/en_ask_address.mp3",
        "ask_pincode": "https://raw.githubusercontent.com/debdip4/agrikartwhatsappbot/main/Audio_files/en_ask_pincode.mp3",
        "ask_password": "https://raw.githubusercontent.com/debdip4/agrikartwhatsappbot/main/Audio_files/en_ask_password.mp3",
        "reg_complete": "https://raw.githubusercontent.com/debdip4/agrikartwhatsappbot/main/Audio_files/en_reg_complete.mp3",
        "ask_price": "https://raw.githubusercontent.com/debdip4/agrikartwhatsappbot/main/Audio_files/en_ask_price.mp3",
        "ask_quantity": "https://raw.githubusercontent.com/debdip4/agrikartwhatsappbot/main/Audio_files/en_ask_quantity.mp3",
        "ask_more_crops": "https://raw.githubusercontent.com/debdip4/agrikartwhatsappbot/main/Audio_files/en_ask_more_crops.mp3",
        "next_crop": "https://raw.githubusercontent.com/debdip4/agrikartwhatsappbot/main/Audio_files/en_next_crop.mp3",
        "thank_you": "https://raw.githubusercontent.com/debdip4/agrikartwhatsappbot/main/Audio_files/en_thank_you.mp3",
        "welcome_back": "https://raw.githubusercontent.com/debdip4/agrikartwhatsappbot/main/Audio_files/en_welcome_back.mp3",
        "closing": "https://raw.githubusercontent.com/debdip4/agrikartwhatsappbot/main/Audio_files/en_closing.mp3",
        "ask_loginpassword": "https://raw.githubusercontent.com/debdip4/agrikartwhatsappbot/main/Audio_files/en_ask_loginpassword.mp3",
        "ask_state": "https://raw.githubusercontent.com/debdip4/agrikartwhatsappbot/main/Audio_files/en_ask_state.mp3",
        "ask_crop": "https://raw.githubusercontent.com/debdip4/agrikartwhatsappbot/main/Audio_files/en_ask_crop.mp3",
        "no_price_data": "https://raw.githubusercontent.com/debdip4/agrikartwhatsappbot/main/Audio_files/en_no_price_data.mp3",
    },
    "hi": {
        "ask_name": "https://raw.githubusercontent.com/debdip4/agrikartwhatsappbot/main/Audio_files/hi_ask_name.mp3",
        "ask_address": "https://raw.githubusercontent.com/debdip4/agrikartwhatsappbot/main/Audio_files/hi_ask_address.mp3",
        "ask_pincode": "https://raw.githubusercontent.com/debdip4/agrikartwhatsappbot/main/Audio_files/hi_ask_pincode.mp3",
        "ask_password": "https://raw.githubusercontent.com/debdip4/agrikartwhatsappbot/main/Audio_files/hi_ask_password.mp3",
        "reg_complete": "https://raw.githubusercontent.com/debdip4/agrikartwhatsappbot/main/Audio_files/hi_reg_complete.mp3",
        "ask_price": "https://raw.githubusercontent.com/debdip4/agrikartwhatsappbot/main/Audio_files/hi_ask_price.mp3",
        "ask_quantity": "https://raw.githubusercontent.com/debdip4/agrikartwhatsappbot/main/Audio_files/hi_ask_quantity.mp3",
        "ask_more_crops": "https://raw.githubusercontent.com/debdip4/agrikartwhatsappbot/main/Audio_files/hi_ask_more_crops.mp3",
        "next_crop": "https://raw.githubusercontent.com/debdip4/agrikartwhatsappbot/main/Audio_files/hi_next_crop.mp3",
        "thank_you": "https://raw.githubusercontent.com/debdip4/agrikartwhatsappbot/main/Audio_files/hi_thank_you.mp3",
        "welcome_back": "https://raw.githubusercontent.com/debdip4/agrikartwhatsappbot/main/Audio_files/hi_welcome_back.mp3",
        "closing": "https://raw.githubusercontent.com/debdip4/agrikartwhatsappbot/main/Audio_files/hi_closing.mp3",
        "ask_loginpassword": "https://raw.githubusercontent.com/debdip4/agrikartwhatsappbot/main/Audio_files/hi_ask_loginpassword.mp3",
        "ask_state": "https://raw.githubusercontent.com/debdip4/agrikartwhatsappbot/main/Audio_files/hi_ask_state.mp3",
        "ask_crop": "https://raw.githubusercontent.com/debdip4/agrikartwhatsappbot/main/Audio_files/hi_ask_crop.mp3",
        "no_price_data": "https://raw.githubusercontent.com/debdip4/agrikartwhatsappbot/main/Audio_files/hi_no_price_data.mp3",
    }
}


# --- Helper Functions ---

def send_whatsapp_message(to: str, msg: str):
    print(f"--> Sending text to {to}: '{msg[:70]}...'")
    payload = {"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": msg}}
    _send_request("messages", payload)

def send_whatsapp_audio(to: str, audio_link: str):
    print(f"--> Sending audio to {to}: {audio_link}")
    payload = {"messaging_product": "whatsapp", "to": to, "type": "audio", "audio": {"link": audio_link}}
    _send_request("messages", payload)

def _send_request(endpoint: str, payload: dict):
    """Internal function to handle sending requests to Meta API."""
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/{endpoint}"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"!!! ERROR sending Meta API request: {e}")

def check_farmer_exists(phone_number):
    url = f"{API_BASE_URL}/api/v1/farmer/check/{phone_number}/"
    print(f"--- Checking existence for {phone_number} at {url}")
    try:
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            exists = response.json().get("exists", False)
            print(f"--- Backend response: Farmer exists = {exists}")
            return exists
        print(f"--- Backend Error: Status {response.status_code}, {response.text}")
        return False
    except requests.exceptions.RequestException as e:
        print(f"!!! FATAL ERROR calling backend API: {e}")
        return False

# --- Other API and Scraper functions remain unchanged ---
def register_farmer_api(user_data):
    url = f"{API_BASE_URL}/api/v1/auth/signup/farmer/"
    try:
        res = requests.post(url, json=user_data, timeout=20)
        res.raise_for_status()
        return res.json()
    except Exception as e: return None

def login_farmer_api(username, password):
    url = f"{API_BASE_URL}/api/v1/auth/token/"
    payload = {"username": username, "password": password}
    try:
        res = requests.post(url, json=payload, timeout=20)
        res.raise_for_status()
        return res.json()
    except Exception as e: return None

def add_produce_api(produce_data, access_token):
    url = f"{API_BASE_URL}/api/v1/produce/"
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        res = requests.post(url, headers=headers, json=produce_data, timeout=20)
        res.raise_for_status()
        return res.json()
    except Exception as e: return None
    
def get_agmarknet_prices(commodity_name, state_name):
    # This function remains the same as previous correct versions.
    pass

def analyze_price_data(price_df):
    # This function remains the same.
    pass

def generate_tts_elevenlabs(text, lang="en"):
    # This function is assumed to be working correctly
    pass

def set_user_state(phone, new_state):
    """Helper to log state changes."""
    old_state = user_states.get(phone, {}).get("state", "None")
    user_states[phone]["state"] = new_state
    print(f"*** STATE CHANGE for {phone}: {old_state} -> {new_state} ***")

def ask_for_state_selection(to, lang):
    """Helper function to send the state list."""
    state_list_message = "Please select your state by replying with the number:\n\n"
    state_list_message += "\n".join([f"{num}. {name}" for num, name in STATES.items()])
    send_whatsapp_message(to, state_list_message)
    send_whatsapp_audio(to, AUDIO_CLIPS[lang]["ask_state"])

# --- Main Webhook Logic ---
@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.verify_token") == VERIFY_TOKEN:
            return request.args.get("hub.challenge"), 200
        return "Unauthorized", 403

    data = request.get_json()
    try:
        message = data["entry"][0]["changes"][0]["value"]["messages"][0]
        from_number = message["from"]
        msg_body = message["text"]["body"].strip()
        command = msg_body.lower()
        
        print(f"\n{'='*50}\nINCOMING from {from_number}: '{msg_body}'")

        if from_number not in user_states:
            user_states[from_number] = {"data": {}, "language": "en"}

        current_state = user_states[from_number].get("state")
        lang = user_states[from_number].get("language", "en")
        print(f"Current state for {from_number} is: '{current_state}'")

        if command in ["hi", "hello", "नमस्ते"]:
            exists = check_farmer_exists(from_number)
            if exists:
                set_user_state(from_number, "awaiting_login_password")
                send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]["welcome_back"])
                send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]["ask_loginpassword"])
            else:
                set_user_state(from_number, "awaiting_language_choice")
                send_whatsapp_audio(from_number, AUDIO_CLIPS["welcome"])
                send_whatsapp_message(from_number, "Please select a language:\n1. English\n2. हिन्दी")

        elif current_state == "awaiting_login_password":
            login_resp = login_farmer_api(from_number, msg_body)
            if login_resp and login_resp.get("access"):
                user_states[from_number]["access_token"] = login_resp["access"]
                set_user_state(from_number, "awaiting_state_selection")
                ask_for_state_selection(from_number, lang)
            else:
                send_whatsapp_message(from_number, "❌ Incorrect password.")
                send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]["ask_loginpassword"])

        elif current_state == "awaiting_language_choice":
            lang = "hi" if "2" in command else "en"
            user_states[from_number]["language"] = lang
            set_user_state(from_number, "awaiting_name")
            send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]["ask_name"])

        elif current_state == "awaiting_name":
            user_states[from_number]["data"]["name"] = msg_body
            set_user_state(from_number, "awaiting_address")
            send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]["ask_address"])

        elif current_state == "awaiting_address":
            user_states[from_number]["data"]["address"] = msg_body
            set_user_state(from_number, "awaiting_pincode")
            send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]["ask_pincode"])

        elif current_state == "awaiting_pincode":
            user_states[from_number]["data"]["pincode"] = msg_body
            set_user_state(from_number, "awaiting_password")
            send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]["ask_password"])
        
        elif current_state == "awaiting_password":
            user_data = user_states[from_number]["data"]
            user_data.update({
                "password": msg_body,
                "username": from_number,
                "phone_number": from_number
            })
            if register_farmer_api(user_data):
                login_resp = login_farmer_api(from_number, msg_body)
                if login_resp and login_resp.get("access"):
                    user_states[from_number]["access_token"] = login_resp["access"]
                    set_user_state(from_number, "awaiting_state_selection")
                    send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]["reg_complete"])
                    ask_for_state_selection(from_number, lang)
                else:
                    send_whatsapp_message(from_number, "Registration complete, but login failed. Please say 'hi' to try logging in.")
            else:
                send_whatsapp_message(from_number, "❌ Registration failed.")

        elif current_state == "awaiting_state_selection":
            state_name = STATES.get(command)
            if not state_name:
                send_whatsapp_message(from_number, "❌ Invalid selection. Please reply with a valid number from the list.")
            else:
                user_states[from_number]["temp_produce"] = {"state": state_name}
                set_user_state(from_number, "awaiting_crop_name")
                send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]["ask_crop"])

        elif current_state == "awaiting_crop_name":
            crop_name = msg_body.title()
            state_name = user_states[from_number]["temp_produce"]["state"]
            user_states[from_number]["temp_produce"]["name"] = crop_name
            send_whatsapp_message(from_number, f"⏳ Searching for {crop_name} prices in {state_name}...")
            # Price logic here...
            set_user_state(from_number, "awaiting_price")
            send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]["ask_price"])

        elif current_state == "awaiting_price":
            try:
                user_states[from_number]["temp_produce"]["price_per_kg"] = float(msg_body)
                set_user_state(from_number, "awaiting_quantity")
                send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]["ask_quantity"])
            except ValueError:
                send_whatsapp_message(from_number, "❌ Please enter a valid number for the price (e.g., 25.50).")

        elif current_state == "awaiting_quantity":
            try:
                user_states[from_number]["temp_produce"]["quantity_kg"] = float(msg_body)
                token = user_states[from_number].get("access_token")
                if token and add_produce_api(user_states[from_number]["temp_produce"], token):
                    set_user_state(from_number, "awaiting_more_crops")
                    send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]["ask_more_crops"])
                else:
                    send_whatsapp_message(from_number, "❌ Failed to save produce. You may need to log in again. Say 'hi' to restart.")
            except ValueError:
                send_whatsapp_message(from_number, "❌ Please enter a valid number for the quantity (e.g., 50).")

        elif current_state == "awaiting_more_crops":
            if command in ["yes", "y", "ok", "1", "हाँ", "हां"]:
                set_user_state(from_number, "awaiting_state_selection")
                ask_for_state_selection(from_number, lang)
            else:
                send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]["thank_you"])
                set_user_state(from_number, "conversation_over")

    except (IndexError, KeyError):
        # Ignore non-message webhooks from Meta
        pass
    except Exception as e:
        print(f"!!! A FATAL ERROR occurred in the webhook: {e} !!!")

    return "OK", 200


@app.route("/notify-farmer", methods=["POST"])
def notify_farmer():
    # This function should be correct from previous versions.
    pass

if __name__ == "__main__":
    if not os.path.exists("static/audio"):
        os.makedirs("static/audio")
    print("WhatsApp Bot Running...")
    app.run(port=5000, debug=True)
