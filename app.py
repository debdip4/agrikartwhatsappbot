import os
import re
from flask import Flask, request, jsonify
import requests
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import NoSuchElementException
import pandas as pd
import time

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# --- Environment Variables ---
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
BACKEND_API_BASE_URL = os.getenv("BACKEND_API_BASE_URL")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")

# --- Audio and Text Resources ---
AUDIO_CLIPS = {
    "welcome": "https://raw.githubusercontent.com/debdip4/agrikartwhatsappbot/main/Audio_files/welcome.mp3",
    "en": {
        "ask_name": "https://raw.githubusercontent.com/debdip4/agrikartwhatsappbot/main/Audio_files/en_ask_name.mp3",
        "ask_address": "https://raw.githubusercontent.com/debdip4/agrikartwhatsappbot/main/Audio_files/en_ask_address.mp3",
        "ask_state": "https://raw.githubusercontent.com/debdip4/agrikartwhatsappbot/main/Audio_files/en_ask_state.mp3",
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
    },
    "hi": {
        "ask_name": "https://raw.githubusercontent.com/debdip4/agrikartwhatsappbot/main/Audio_files/hi_ask_name.mp3",
        "ask_address": "https://raw.githubusercontent.com/debdip4/agrikartwhatsappbot/main/Audio_files/hi_ask_address.mp3",
        "ask_state": "https://raw.githubusercontent.com/debdip4/agrikartwhatsappbot/main/Audio_files/hi_ask_state.mp3",
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
    }
}

CATEGORIES = {
    "en": {
        "1": "Fruits",
        "2": "Vegetables",
        "3": "Organic",
        "4": "Dairy & Eggs",
        "5": "Grains & Pulses",
    },
    "hi": {
        "1": "फल (Fruits)",
        "2": "सब्जियां (Vegetables)",
        "3": "जैविक (Organic)",
        "4": "डेयरी और अंडे (Dairy & Eggs)",
        "5": "अनाज और दालें (Grains & Pulses)",
    }
}

PRODUCE_LIST = {
    "Fruits": ["Apple", "Banana", "Grapes", "Mango", "Orange", "Papaya", "Pineapple"],
    "Vegetables": ["Potato", "Onion", "Tomato", "Carrot", "Cauliflower", "Brinjal", "Lady's Finger"],
    "Grains & Pulses": ["Rice", "Wheat", "Maize", "Paddy", "Masur Dal", "Moong Dal", "Arhar Dal"],
    "Organic": ["Organic Apple", "Organic Tomato", "Organic Rice"],
    "Dairy & Eggs": ["Cow Milk", "Buffalo Milk", "Eggs"]
}

# --- User State Management ---
user_state = {}

# --- Helper Functions ---
def send_whatsapp_message(to, message_type, data):
    """Sends a message to a WhatsApp user."""
    url = f"https://graph.facebook.com/v19.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": message_type,
        message_type: data
    }
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Error sending message: {e}")
        return None

def send_text_message(to, text):
    """Sends a text message."""
    return send_whatsapp_message(to, "text", {"body": text})

def send_audio_message(to, audio_url):
    """Sends an audio message."""
    return send_whatsapp_message(to, "audio", {"link": audio_url})

def get_latest_price(state, commodity):
    """Scrapes the latest price from Agmarknet."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=chrome_options)

    try:
        driver.get("https://agmarknet.gov.in/PriceAndArrivals/DatewiseCommodityReport.aspx")
        time.sleep(2)  # Allow page to load

        Select(driver.find_element(By.ID, "cphBody_cboState")).select_by_visible_text(state)
        time.sleep(2)  # Allow commodity dropdown to populate

        Select(driver.find_element(By.ID, "cphBody_cboCommodity")).select_by_visible_text(commodity)
        driver.find_element(By.ID, "cphBody_btnSubmit").click()
        time.sleep(3)  # Allow report to generate

        table = driver.find_element(By.ID, "cphBody_gridRecords")
        df = pd.read_html(table.get_attribute('outerHTML'))[0]

        # Clean and process data
        df.columns = df.iloc[0]
        df = df[1:]
        df = df.dropna(axis=1, how='all')
        price_series = pd.to_numeric(df['Modal Price (Rs./Quintal)'], errors='coerce')
        avg_price = price_series.mean()

        return round(avg_price / 100, 2) if not pd.isna(avg_price) else None

    except (NoSuchElementException, IndexError) as e:
        app.logger.error(f"Scraping failed for {commodity} in {state}: {e}")
        return None
    finally:
        driver.quit()

# --- Webhook ---
@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        # WhatsApp verification
        if request.args.get('hub.verify_token') == VERIFY_TOKEN:
            return request.args.get('hub.challenge')
        return "Verification token mismatch", 403

    if request.method == 'POST':
        data = request.get_json()
        if data.get('object') == 'whatsapp_business_account':
            for entry in data.get('entry', []):
                for change in entry.get('changes', []):
                    if 'messages' in change.get('value', {}):
                        message = change['value']['messages'][0]
                        phone_number = message['from']
                        message_body = message.get('text', {}).get('body', '').strip()
                        process_message(phone_number, message_body)
        return "OK", 200

# --- Main Logic ---
def process_message(phone, message):
    state = user_state.get(phone, {})
    current_step = state.get("step")

    # --- Initial Greeting & Language Selection ---
    if not current_step:
        # Check if farmer exists
        try:
            response = requests.get(f"{BACKEND_API_BASE_URL}/api/v1/farmer/check/{phone}/")
            if response.status_code == 200:
                user_state[phone] = {"step": "login_password"}
                lang = response.json().get("language", "en") # Assuming backend stores language
                user_state[phone]["lang"] = lang
                send_audio_message(phone, AUDIO_CLIPS[lang]["welcome_back"])
                send_audio_message(phone, AUDIO_CLIPS[lang]["ask_loginpassword"])
            else:
                 user_state[phone] = {"step": "language_select"}
                 send_audio_message(phone, AUDIO_CLIPS["welcome"])
        except requests.RequestException as e:
            app.logger.error(f"Backend check failed: {e}")
            send_text_message(phone, "Sorry, we're having trouble connecting. Please try again later.")
        return

    lang = state.get("lang", "en") # Default to English

    # --- Conversation Flows ---
    if message.lower() in ['hi', 'hello']:
         # Reset for returning user
         user_state[phone] = {}
         process_message(phone, "") # Restart the flow
         return

    if message.lower() == 'thank you':
        send_audio_message(phone, AUDIO_CLIPS[lang]["closing"])
        user_state.pop(phone, None) # End session
        return

    # --- Registration Flow ---
    if current_step == "language_select":
        if message == "1":
            user_state[phone]["lang"] = "en"
        elif message == "2":
            user_state[phone]["lang"] = "hi"
        else:
            send_text_message(phone, "Please select 1 for English or 2 for Hindi.")
            return

        lang = user_state[phone]["lang"]
        user_state[phone]["step"] = "ask_name"
        send_audio_message(phone, AUDIO_CLIPS[lang]["ask_name"])
        return

    elif current_step == "ask_name":
        user_state[phone]["name"] = message
        user_state[phone]["step"] = "ask_address"
        send_audio_message(phone, AUDIO_CLIPS[lang]["ask_address"])

    elif current_step == "ask_address":
        user_state[phone]["address"] = message
        user_state[phone]["step"] = "ask_state"
        send_audio_message(phone, AUDIO_CLIPS[lang]["ask_state"])
        # You might want to send a text list of states here for easier selection
        # For now, we assume user types the state name correctly
        # send_text_message(phone, "Please type your state name from the list: ...")

    elif current_step == "ask_state":
        user_state[phone]["state"] = message
        user_state[phone]["step"] = "ask_pincode"
        send_audio_message(phone, AUDIO_CLIPS[lang]["ask_pincode"])

    elif current_step == "ask_pincode":
        if not re.match(r'^\d{6}$', message):
            send_text_message(phone, "Invalid Pincode. Please enter a 6-digit pincode.")
            return
        user_state[phone]["pincode"] = message
        user_state[phone]["step"] = "ask_password"
        send_audio_message(phone, AUDIO_CLIPS[lang]["ask_password"])

    elif current_step == "ask_password":
        user_state[phone]["password"] = message
        # --- Attempt Registration ---
        try:
            signup_data = {
                "name": user_state[phone]["name"],
                "phone": phone,
                "password": user_state[phone]["password"],
                "address": user_state[phone]["address"],
                "state": user_state[phone]["state"],
                "pincode": user_state[phone]["pincode"],
                "language": lang
            }
            response = requests.post(f"{BACKEND_API_BASE_URL}/api/v1/auth/signup/farmer/", json=signup_data)
            response.raise_for_status()
            # Successfully registered, now log in to get token
            login_data = {"phone": phone, "password": user_state[phone]["password"]}
            token_response = requests.post(f"{BACKEND_API_BASE_URL}/api/v1/auth/token/", json=login_data)
            token_response.raise_for_status()
            user_state[phone]["token"] = token_response.json().get('access')

            user_state[phone]["step"] = "select_category"
            send_audio_message(phone, AUDIO_CLIPS[lang]["reg_complete"])
            category_text = "Please select a category for your first crop:\n" if lang == "en" else "कृपया अपनी पहली फसल के लिए एक श्रेणी चुनें:\n"
            for num, cat in CATEGORIES[lang].items():
                category_text += f"{num}. {cat}\n"
            send_text_message(phone, category_text)

        except requests.RequestException as e:
            app.logger.error(f"Registration/Login failed: {e}")
            error_msg = e.response.json() if e.response else str(e)
            send_text_message(phone, f"Registration failed: {error_msg}. Please try again, starting with 'hi'.")
            user_state.pop(phone, None) # Reset state

    # --- Login Flow ---
    elif current_step == "login_password":
        password = message
        try:
            login_data = {"phone": phone, "password": password}
            token_response = requests.post(f"{BACKEND_API_BASE_URL}/api/v1/auth/token/", json=login_data)
            token_response.raise_for_status()
            user_state[phone]["token"] = token_response.json().get('access')

            user_state[phone]["step"] = "select_category"
            send_audio_message(phone, AUDIO_CLIPS[lang]["next_crop"])
            category_text = "Please select a category:\n" if lang == "en" else "कृपया एक श्रेणी चुनें:\n"
            for num, cat in CATEGORIES[lang].items():
                category_text += f"{num}. {cat}\n"
            send_text_message(phone, category_text)

        except requests.RequestException:
            send_text_message(phone, "Login failed. Incorrect password. Please try again.")
            # We stay at the "login_password" step

    # --- Produce Listing Flow ---
    elif current_step == "select_category":
        category_en_name = CATEGORIES["en"].get(message)
        if not category_en_name:
            send_text_message(phone, "Invalid selection. Please choose a number from the list.")
            return

        user_state[phone]["produce"] = {"category": category_en_name}
        user_state[phone]["step"] = "select_produce"

        produce_text = f"Select a produce from {category_en_name}:\n"
        for i, item in enumerate(PRODUCE_LIST.get(category_en_name, []), 1):
             produce_text += f"{i}. {item}\n"
        send_text_message(phone, produce_text)

    elif current_step == "select_produce":
        try:
            selection_index = int(message) - 1
            category = user_state[phone]["produce"]["category"]
            selected_produce = PRODUCE_LIST[category][selection_index]
            user_state[phone]["produce"]["name"] = selected_produce

            send_text_message(phone, f"Fetching latest price for {selected_produce} in {user_state[phone]['state']}...")
            suggested_price = get_latest_price(user_state[phone]['state'], selected_produce)

            price_message = ""
            if suggested_price:
                 price_message = (f"The current average price is around ₹{suggested_price} per kg. " if lang == "en"
                                  else f"वर्तमान औसत मूल्य लगभग ₹{suggested_price} प्रति किलोग्राम है। ")

            send_text_message(phone, price_message)
            send_audio_message(phone, AUDIO_CLIPS[lang]["ask_price"])
            user_state[phone]["step"] = "ask_price"

        except (ValueError, IndexError):
            send_text_message(phone, "Invalid selection. Please choose a number from the list.")

    elif current_step == "ask_price":
        try:
            price = float(message)
            user_state[phone]["produce"]["price_per_kg"] = price
            user_state[phone]["step"] = "ask_quantity"
            send_audio_message(phone, AUDIO_CLIPS[lang]["ask_quantity"])
        except ValueError:
            send_text_message(phone, "Please enter a valid price (e.g., 50 or 50.5).")

    elif current_step == "ask_quantity":
        try:
            quantity = float(message)
            user_state[phone]["produce"]["quantity_kg"] = quantity

            # --- Add Produce to Backend ---
            try:
                produce_data = {
                    "name": user_state[phone]["produce"]["name"],
                    "price": float(user_state[phone]["produce"]["price_per_kg"]),
                    "quantity": float(user_state[phone]["produce"]["quantity_kg"]),
                    "category": user_state[phone]["produce"]["category"]
                }
                headers = {"Authorization": f"Bearer {user_state[phone]['token']}"}
                response = requests.post(f"{BACKEND_API_BASE_URL}/api/v1/produce/", json=produce_data, headers=headers)
                response.raise_for_status()

                user_state[phone]["step"] = "ask_more_crops"
                send_audio_message(phone, AUDIO_CLIPS[lang]["ask_more_crops"])
                more_crops_text = "1. Yes\n2. No" if lang == "en" else "१. हाँ\n२. नहीं"
                send_text_message(phone, more_crops_text)

            except requests.RequestException as e:
                app.logger.error(f"Failed to add produce: {e}")
                send_text_message(phone, "Sorry, there was an error listing your produce. Please try again later.")
                user_state.pop(phone, None)

        except ValueError:
            send_text_message(phone, "Please enter a valid quantity in kg (e.g., 100 or 150.5).")


    elif current_step == "ask_more_crops":
        if message == "1": # Yes
            user_state[phone]["step"] = "select_category"
            send_audio_message(phone, AUDIO_CLIPS[lang]["next_crop"])
            category_text = "Please select a category:\n" if lang == "en" else "कृपया एक श्रेणी चुनें:\n"
            for num, cat in CATEGORIES[lang].items():
                category_text += f"{num}. {cat}\n"
            send_text_message(phone, category_text)
        elif message == "2": # No
            send_audio_message(phone, AUDIO_CLIPS[lang]["thank_you"])
            user_state.pop(phone, None) # End session
        else:
            send_text_message(phone, "Invalid option. Please select 1 for Yes or 2 for No.")

# --- Notification Endpoint ---
@app.route('/notify', methods=['POST'])
def notify_farmer():
    """Endpoint for the main website to call when a sale occurs."""
    data = request.get_json()
    if not data or 'phone' not in data or 'message' not in data:
        return jsonify({"error": "Missing 'phone' or 'message' in request body"}), 400

    phone_number = data['phone']
    message_text = data['message']

    result = send_text_message(phone_number, message_text)
    if result:
        return jsonify({"status": "Notification sent successfully"}), 200
    else:
        return jsonify({"status": "Failed to send notification"}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
