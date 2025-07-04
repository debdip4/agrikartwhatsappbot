import os
import json
import requests
import time
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# --- Price Bot Imports ---
import pandas as pd
from io import StringIO
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from statistics import mean


app = Flask(__name__)

# --- Load Credentials ---
ACCESS_TOKEN = os.environ['ACCESS_TOKEN']
VERIFY_TOKEN = os.environ['VERIFY_TOKEN']
PHONE_NUMBER_ID = os.environ['PHONE_NUMBER_ID']
API_BASE_URL = os.environ['BACKEND_API_BASE_URL']

# --- In-memory database for hackathon prototype ---
user_states = {}

# --- Dictionary with Corrected Audio File URLs ---
AUDIO_BASE_URL = "https://raw.githubusercontent.com/debdip4/agrikartwhatsappbot/main/Audio_files/"
AUDIO_CLIPS = {
    'welcome': f"{AUDIO_BASE_URL}welcome.mp3",
    'en': {
        'ask_name': f"{AUDIO_BASE_URL}en_ask_name.mp3",
        'ask_address': f"{AUDIO_BASE_URL}en_ask_address.mp3",
        'ask_pincode': f"{AUDIO_BASE_URL}en_ask_pincode.mp3",
        'ask_state': f"{AUDIO_BASE_URL}en_ask_state.mp3",
        'ask_password': f"{AUDIO_BASE_URL}en_ask_password.mp3",
        'reg_complete': f"{AUDIO_BASE_URL}en_reg_complete.mp3",
        'ask_price': f"{AUDIO_BASE_URL}en_ask_price.mp3",
        'ask_quantity': f"{AUDIO_BASE_URL}en_ask_quantity.mp3",
        'ask_more_crops': f"{AUDIO_BASE_URL}en_ask_more_crops.mp3",
        'next_crop': f"{AUDIO_BASE_URL}en_next_crop.mp3",
        'thank_you': f"{AUDIO_BASE_URL}en_thank_you.mp3",
        'welcome_back': f"{AUDIO_BASE_URL}en_welcome_back.mp3",
        'closing': f"{AUDIO_BASE_URL}en_closing.mp3",
        'ask_loginpassword': f"{AUDIO_BASE_URL}en_ask_loginpassword.mp3",
    },
    'hi': {
        'ask_name': f"{AUDIO_BASE_URL}hi_ask_name.mp3",
        'ask_address': f"{AUDIO_BASE_URL}hi_ask_address.mp3",
        'ask_pincode': f"{AUDIO_BASE_URL}hi_ask_pincode.mp3",
        'ask_state': f"{AUDIO_BASE_URL}hi_ask_state.mp3",
        'ask_password': f"{AUDIO_BASE_URL}hi_ask_password.mp3",
        'reg_complete': f"{AUDIO_BASE_URL}hi_reg_complete.mp3",
        'ask_price': f"{AUDIO_BASE_URL}hi_ask_price.mp3",
        'ask_quantity': f"{AUDIO_BASE_URL}hi_ask_quantity.mp3",
        'ask_more_crops': f"{AUDIO_BASE_URL}hi_ask_more_crops.mp3",
        'next_crop': f"{AUDIO_BASE_URL}hi_next_crop.mp3",
        'thank_you': f"{AUDIO_BASE_URL}hi_thank_you.mp3",
        'welcome_back': f"{AUDIO_BASE_URL}hi_welcome_back.mp3",
        'closing': f"{AUDIO_BASE_URL}hi_closing.mp3",
        'ask_loginpassword': f"{AUDIO_BASE_URL}hi_ask_loginpassword.mp3",
    }
}

# --- Price Bot Functions ---
def get_agmarknet_prices(commodity_name: str, state_name: str):
    print(f"Starting price scraper for {commodity_name} in {state_name}...")
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    driver = None
    try:
        driver = webdriver.Chrome(options=options)
        url = "https://agmarknet.gov.in/SearchCmmMkt.aspx"
        driver.get(url)
        driver.set_page_load_timeout(30)
        Select(driver.find_element(By.ID, "ddlCommodity")).select_by_visible_text(commodity_name)
        Select(driver.find_element(By.ID, "ddlState")).select_by_visible_text(state_name)
        driver.find_element(By.ID, "btnGo").click()
        wait = WebDriverWait(driver, 20)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#cphBody_GridPriceData tbody tr")))
        print("Data table loaded from Agmarknet.")
        table_html = driver.find_element(By.ID, "cphBody_GridPriceData").get_attribute('outerHTML')
        df_list = pd.read_html(StringIO(table_html))
        if not df_list: return None
        df = df_list[0]
        if 'No Data Found' in df.to_string(): return None
        return df
    except TimeoutException:
        print(f"Timed out waiting for data for '{commodity_name}' in '{state_name}'.")
        return None
    except Exception as e:
        print(f"An error occurred during scraping: {e}")
        return None
    finally:
        if driver:
            driver.quit()

def analyze_price_data(price_df: pd.DataFrame):
    if len(price_df.columns) == 12:
        price_df.columns = ['Sl No.', 'State', 'District', 'Market', 'Group', 'Commodity', 'Variety', 'Grade', 'Min Price', 'Max Price', 'Modal Price (Rs./Quintal)', 'Date']
    price_col = 'Modal Price (Rs./Quintal)'
    modal_prices = pd.to_numeric(price_df[price_col], errors='coerce').dropna()
    if modal_prices.empty:
        return None
    return {
        "market_count": len(modal_prices),
        "min_price": modal_prices.min(),
        "max_price": modal_prices.max(),
        "avg_price": round(modal_prices.mean(), 2)
    }

# --- API Helpers ---
def check_farmer_exists(phone_number):
    url = f"{API_BASE_URL}/api/v1/farmer/check/{phone_number}/"
    try:
        response = requests.get(url)
        return response.status_code == 200 and response.json().get("exists", False)
    except requests.exceptions.RequestException as e:
        print(f"ERROR checking farmer existence: {e}")
        return False

def register_farmer_api(user_data):
    url = f"{API_BASE_URL}/api/v1/auth/signup/farmer/"
    payload = {
        "username": user_data['username'],
        "password": user_data['password'],
        "email": f"{user_data['username']}@agrikart.ai",
        "phone_number": user_data['phone_number'],
        "name": user_data['name'],
        "address": user_data['address'],
        "pincode": user_data.get('pincode', ''),
        "state": user_data.get('state', '')
    }
    try:
        res = requests.post(url, json=payload)
        res.raise_for_status()
        return res.json()
    except Exception as e:
        print(f"Error in register_farmer_api: {e}")
        return None

def login_farmer_api(username, password):
    url = f"{API_BASE_URL}/api/v1/auth/token/"
    payload = {"username": username, "password": password}
    try:
        res = requests.post(url, json=payload)
        res.raise_for_status()
        return res.json()
    except Exception as e:
        print(f"Error in login_farmer_api: {e}")
        return None

def add_produce_api(produce_data, access_token):
    url = f"{API_BASE_URL}/api/v1/produce/"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    payload = {
        "name": produce_data['name'],
        "price": float(produce_data['price_per_kg']),
        "quantity": float(produce_data['quantity_kg']),
        "category": "Others"
    }
    try:
        res = requests.post(url, headers=headers, json=payload)
        res.raise_for_status()
        return res.json()
    except Exception as e:
        print(f"Error in add_produce_api: {e}")
        return None

# --- Messaging Helpers ---
def send_whatsapp_message(to, msg):
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    payload = {"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": msg}}
    requests.post(url, headers=headers, json=payload)

def send_whatsapp_audio(to, url_link):
    if not url_link:
        print("send_whatsapp_audio called with no URL.")
        return
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    payload = {"messaging_product": "whatsapp", "to": to, "type": "audio", "audio": {"link": url_link}}
    requests.post(url, headers=headers, json=payload)


# --- Webhook ---
@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        if request.args.get('hub.mode') == 'subscribe' and request.args.get('hub.verify_token') == VERIFY_TOKEN:
            return request.args.get('hub.challenge'), 200
        return 'Unauthorized', 403

    data = request.get_json()
    try:
        message = data["entry"][0]["changes"][0]["value"]["messages"][0]
        from_number = message['from']
        
        if 'text' in message:
            msg_body = message['text']['body']
        else:
            send_whatsapp_message(from_number, "I can only understand text messages for now.")
            return 'OK', 200
        
        command = msg_body.strip().lower()
        print(f"Message from {from_number}: '{command}'")

        if from_number not in user_states: user_states[from_number] = {"data": {}}
        current_state = user_states[from_number].get("state")
        print(f"Current state for {from_number}: {current_state}")

        if command in ['hi', 'hello', 'नमस्ते']:
            if check_farmer_exists(from_number):
                user_states[from_number]['state'] = 'awaiting_lang_after_exists'
                send_whatsapp_audio(from_number, AUDIO_CLIPS['welcome'])
            else:
                user_states[from_number]['state'] = 'awaiting_language_choice'
                send_whatsapp_audio(from_number, AUDIO_CLIPS['welcome'])
            return 'OK', 200

        # --- State Machine ---
        if current_state == 'awaiting_lang_after_exists':
            lang = 'en' if '1' in command else 'hi'
            user_states[from_number]['language'] = lang
            send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]['ask_loginpassword'])
            user_states[from_number]['state'] = 'awaiting_password'

        elif current_state == 'awaiting_language_choice':
            lang = 'en' if '1' in command else 'hi'
            user_states[from_number]['language'] = lang
            user_states[from_number]['state'] = 'awaiting_name'
            send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]['ask_name'])

        elif current_state == 'awaiting_name':
            lang = user_states[from_number]['language']
            user_states[from_number]['data']['name'] = msg_body
            user_states[from_number]['state'] = 'awaiting_address'
            send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]['ask_address'])

        elif current_state == 'awaiting_address':
            lang = user_states[from_number]['language']
            user_states[from_number]['data']['address'] = msg_body
            user_states[from_number]['state'] = 'awaiting_pincode'
            send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]['ask_pincode'])
        
        elif current_state == 'awaiting_pincode':
            lang = user_states[from_number]['language']
            user_states[from_number]['data']['pincode'] = msg_body.strip()
            user_states[from_number]['state'] = 'awaiting_state'
            send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]['ask_state'])
        
        elif current_state == 'awaiting_state':
            lang = user_states[from_number]['language']
            user_states[from_number]['data']['state'] = msg_body.strip().title()
            user_states[from_number]['state'] = 'awaiting_password'
            send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]['ask_password'])

        elif current_state == 'awaiting_password':
            lang = user_states[from_number]['language']
            user_states[from_number]['data']['password'] = msg_body
            user_states[from_number]['data']['username'] = from_number
            user_states[from_number]['data']['phone_number'] = from_number
            
            if check_farmer_exists(from_number):
                login_resp = login_farmer_api(from_number, msg_body)
                if login_resp and login_resp.get('access'):
                    user_states[from_number]['access_token'] = login_resp['access']
                    user_states[from_number]['state'] = 'awaiting_crop_name'
                    send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]['welcome_back'])
                else:
                    send_whatsapp_message(from_number, "Wrong password. Please try again.")
            else:
                if register_farmer_api(user_states[from_number]['data']):
                    login_resp = login_farmer_api(from_number, msg_body)
                    if login_resp and login_resp.get('access'):
                        user_states[from_number]['access_token'] = login_resp['access']
                        user_states[from_number]['state'] = 'awaiting_crop_name'
                        send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]['reg_complete'])
                    else:
                        send_whatsapp_message(from_number, "Login after registration failed. Try again with 'hi'.")
                else:
                    send_whatsapp_message(from_number, "Registration failed. Try again with 'hi'.")

        elif current_state == 'awaiting_crop_name':
            lang = user_states[from_number]['language']
            crop_name = msg_body.strip().title()
            user_states[from_number]['temp_produce'] = {'name': crop_name}

            state_name = user_states[from_number].get('data', {}).get('state')
            if not state_name:
                send_whatsapp_message(from_number, "Your state is not on file. Please restart by sending 'hi'.")
                return 'OK', 200

            price_df = get_agmarknet_prices(crop_name, state_name)
            if price_df is not None:
                price_summary = analyze_price_data(price_df)
                if price_summary:
                    min_p, max_p, avg_p = price_summary['min_price'], price_summary['max_price'], price_summary['avg_price']
                    suggestion_text = (
                        f"Suggestion:\nPrices for {crop_name} in {state_name} range from Rs.{min_p:.0f} to Rs.{max_p:.0f} per quintal. The average price is Rs.{avg_p:.0f}."
                        if lang == 'en' else
                        f"सुझाव:\n{state_name} में {crop_name} का भाव Rs.{min_p:.0f} से Rs.{max_p:.0f} प्रति क्विंटल के बीच है। औसत भाव Rs.{avg_p:.0f} है।"
                    )
                    send_whatsapp_message(from_number, suggestion_text)
                else:
                    send_whatsapp_message(from_number, "Not enough data to suggest a price.")
            else:
                send_whatsapp_message(from_number, f"Sorry, could not find any recent price data for {crop_name} in {state_name}.")

            user_states[from_number]['state'] = 'awaiting_price'
            send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]['ask_price'])

        elif current_state == 'awaiting_price':
            lang = user_states[from_number]['language']
            user_states[from_number]['temp_produce']['price_per_kg'] = msg_body
            user_states[from_number]['state'] = 'awaiting_quantity'
            send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]['ask_quantity'])

        elif current_state == 'awaiting_quantity':
            lang = user_states[from_number]['language']
            user_states[from_number]['temp_produce']['quantity_kg'] = msg_body
            token = user_states[from_number].get('access_token')
            if token and add_produce_api(user_states[from_number]['temp_produce'], token):
                user_states[from_number]['state'] = 'awaiting_more_crops'
                send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]['ask_more_crops'])
            else:
                send_whatsapp_message(from_number, "Failed to save produce.")
                user_states[from_number]['state'] = 'awaiting_more_crops'

        elif current_state == 'awaiting_more_crops':
            lang = user_states[from_number]['language']
            if command in ['yes', 'y', 'ok', 'हाँ', 'हां']:
                user_states[from_number]['state'] = 'awaiting_crop_name'
                send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]['next_crop'])
            else:
                user_states[from_number]['state'] = 'conversation_over'
                send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]['thank_you'])

    except Exception as e:
        print(f"Error in webhook: {e}")

    return 'OK', 200


@app.route('/', methods=['GET'])
def health_check():
    return 'OK', 200
