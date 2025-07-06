import os
import json
import requests
import time
import pandas as pd
from flask import Flask, request, jsonify, send_from_directory
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# --- Load Environment Variables ---
load_dotenv()
app = Flask(__name__)

# --- Load Credentials ---
ACCESS_TOKEN = os.getenv('ACCESS_TOKEN')
VERIFY_TOKEN = os.getenv('VERIFY_TOKEN')
PHONE_NUMBER_ID = os.getenv('WHATSAPP_PHONE_NUMBER_ID')
API_BASE_URL = os.getenv('BACKEND_API_BASE_URL')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY')

# --- In-memory database for prototype ---
user_states = {}

# --- Audio and Crop Data ---
AUDIO_CLIPS = {
    "welcome": "https://raw.githubusercontent.com/debdip4/agrikartwhatsappbot/main/Audio_files/welcome.mp3",
    "en": {
        "ask_name": "...",
        "ask_address": "...",
        "ask_state": "...",
        "ask_pincode": "...",
        "ask_password": "...",
        "reg_complete": "...",
        "ask_price": "...",
        "ask_quantity": "...",
        "ask_more_crops": "...",
        "thank_you": "...",
        "welcome_back": "...",
        "ask_loginpassword": "...",
    },
    "hi": {
        "ask_name": "...",
        "ask_address": "...",
        "ask_state": "...",
        "ask_pincode": "...",
        "ask_password": "...",
        "reg_complete": "...",
        "ask_price": "...",
        "ask_quantity": "...",
        "ask_more_crops": "...",
        "thank_you": "...",
        "welcome_back": "...",
        "ask_loginpassword": "...",
    }
}

CROP_CATEGORIES = {
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

PRODUCTS_BY_CATEGORY = {
    "Fruits": ["Apple", "Mango", "Banana", "Grapes", "Orange", "Pineapple"],
    "Vegetables": ["Potato", "Onion", "Tomato", "Carrot", "Cauliflower", "Brinjal"],
    "Organic": ["Organic Honey", "Organic Tea", "Organic Rice"],
    "Dairy & Eggs": ["Milk", "Cheese", "Butter", "Eggs"],
    "Grains & Pulses": ["Wheat", "Rice", "Maize", "Arhar Dal", "Moong Dal"],
}

AGMARKNET_STATES = {
    'Andaman and Nicobar': 'AN', 'Andhra Pradesh': 'AP', 'Arunachal Pradesh': 'AR', 'Assam': 'AS',
    'Bihar': 'BI', 'Chandigarh': 'CH', 'Chhattisgarh': 'CG', 'Dadra and Nagar Haveli': 'DN',
    'Daman and Diu': 'DD', 'Delhi': 'DL', 'Goa': 'GO', 'Gujarat': 'GJ', 'Haryana': 'HR',
    'Himachal Pradesh': 'HP', 'Jammu and Kashmir': 'JK', 'Jharkhand': 'JH', 'Karnataka': 'KA',
    'Kerala': 'KL', 'Lakshadweep': 'LD', 'Madhya Pradesh': 'MP', 'Maharashtra': 'MH', 'Manipur': 'MN',
    'Meghalaya': 'ML', 'Mizoram': 'MZ', 'Nagaland': 'NL', 'Odisha': 'OR', 'Puducherry': 'PY',
    'Punjab': 'PB', 'Rajasthan': 'RJ', 'Sikkim': 'SK', 'Tamil Nadu': 'TN', 'Telangana': 'TG',
    'Tripura': 'TR', 'Uttar Pradesh': 'UP', 'Uttarakhand': 'UT', 'West Bengal': 'WB'
}

def setup_driver():
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(options=chrome_options)

def scrape_agmarknet_prices(state, commodity):
    driver = setup_driver()
    try:
        url = "https://agmarknet.gov.in/PriceAndArrivals/DatewiseCommodityReport.aspx"
        driver.get(url)
        wait = WebDriverWait(driver, 10)

        code = AGMARKNET_STATES.get(state)
        if not code:
            return []
        Select(wait.until(EC.presence_of_element_located((By.ID, "cphBody_cboState")))).select_by_value(code)
        time.sleep(2)
        Select(wait.until(EC.presence_of_element_located((By.ID, "cphBody_cboCommodity")))).select_by_visible_text(commodity)
        driver.find_element(By.ID, "cphBody_btnSubmit").click()
        wait.until(EC.presence_of_element_located((By.ID, "cphBody_gridRecords")))
        tables = pd.read_html(driver.page_source, attrs={'id': 'cphBody_gridRecords'})
        if not tables:
            return []
        df = tables[0][['Market Name', 'Min Price (Rs./Quintal)', 'Max Price (Rs./Quintal)', 'Modal Price (Rs./Quintal)']]
        for col in ['Min Price (Rs./Quintal)', 'Max Price (Rs./Quintal)', 'Modal Price (Rs./Quintal)']:
            df[col.replace('Quintal', 'Kg')] = pd.to_numeric(df[col], errors='coerce') / 100
        return df['Modal Price (Rs./Kg)'].dropna().tolist()
    except:
        return []
    finally:
        driver.quit()

def check_farmer_exists(phone):
    try:
        res = requests.get(f"{API_BASE_URL}/api/v1/farmer/check/{phone}/")
        return res.status_code == 200 and res.json().get("exists", False)
    except:
        return False

def register_farmer_api(data):
    try:
        payload = {
            "username": data['username'],
            "password": data['password'],
            "email": f"{data['username']}@agrikart.ai",
            "phone_number": data['phone_number'],
            "name": data['name'],
            "address": f"{data['address']}, {data['state']} - {data['pincode']}"
        }
        res = requests.post(f"{API_BASE_URL}/api/v1/auth/signup/farmer/", json=payload)
        res.raise_for_status()
        return res.json()
    except:
        return None

def login_farmer_api(username, password):
    try:
        res = requests.post(f"{API_BASE_URL}/api/v1/auth/token/", json={"username": username, "password": password})
        res.raise_for_status()
        return res.json()
    except:
        return None

def add_produce_api(produce, token):
    try:
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        payload = {
            "name": produce['name'],
            "price": float(produce['price_per_kg']),
            "quantity": float(produce['quantity_kg']),
            "category": produce.get('category', 'Others')
        }
        res = requests.post(f"{API_BASE_URL}/api/v1/produce/", headers=headers, json=payload)
        res.raise_for_status()
        return res.json()
    except:
        return None

def send_whatsapp_message(to, msg):
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    payload = {"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": msg}}
    requests.post(url, headers=headers, json=payload)

def send_whatsapp_audio(to, link):
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    payload = {"messaging_product": "whatsapp", "to": to, "type": "audio", "audio": {"link": link}}
    requests.post(url, headers=headers, json=payload)

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        if request.args.get('hub.mode') == 'subscribe' and request.args.get('hub.verify_token') == VERIFY_TOKEN:
            return request.args.get('hub.challenge'), 200
        return 'Unauthorized', 403

    data = request.get_json()
    entry = data.get("entry", [])[0]
    message = entry.get("changes", [])[0].get("value", {}).get("messages", [None])[0]
    if not message:
        return 'OK', 200

    from_number = message['from']
    msg_body = message.get('text', {}).get('body', '').strip()
    cmd = msg_body.lower()

    if from_number not in user_states:
        user_states[from_number] = {"data": {}, "state": None}

    state = user_states[from_number]['state']
    lang = user_states[from_number].get('language', 'en')

    # --- Entry Keywords ---
    if cmd in ['hi', 'hello', 'नमस्ते']:
        exists = check_farmer_exists(from_number)
        user_states[from_number]['state'] = 'awaiting_lang_after_exists' if exists else 'awaiting_language_choice'
        send_whatsapp_audio(from_number, AUDIO_CLIPS['welcome'])
        return 'OK', 200

    # --- Language Choice ---
    if state in ['awaiting_language_choice', 'awaiting_lang_after_exists']:
        is_existing = (state == 'awaiting_lang_after_exists')
        lang = 'hi' if '2' in cmd else 'en'
        user_states[from_number]['language'] = lang
        if is_existing:
            user_states[from_number]['state'] = 'awaiting_password_login'
            send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]['ask_loginpassword'])
        else:
            user_states[from_number]['state'] = 'awaiting_name'
            send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]['ask_name'])
        return 'OK', 200

    # --- Registration Flow ---
    if state == 'awaiting_name':
        user_states[from_number]['data']['name'] = msg_body
        user_states[from_number]['state'] = 'awaiting_address'
        send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]['ask_address'])
        return 'OK', 200

    if state == 'awaiting_address':
        user_states[from_number]['data']['address'] = msg_body
        user_states[from_number]['state'] = 'awaiting_state'
        # sorted list for consistent indexing
        sorted_states = sorted(AGMARKNET_STATES.keys())
        state_text = "Select your state:\n" + "\n".join(f"{i+1}. {s}" for i, s in enumerate(sorted_states))
        send_whatsapp_message(from_number, state_text)
        send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]['ask_state'])
        return 'OK', 200

    if state == 'awaiting_state':
        sorted_states = sorted(AGMARKNET_STATES.keys())
        try:
            idx = int(msg_body) - 1
            if 0 <= idx < len(sorted_states):
                user_states[from_number]['data']['state'] = sorted_states[idx]
                user_states[from_number]['state'] = 'awaiting_pincode'
                send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]['ask_pincode'])
            else:
                send_whatsapp_message(from_number, "Invalid selection; please try again.")
        except ValueError:
            send_whatsapp_message(from_number, "Please reply with the number of your state.")
        return 'OK', 200

    if state == 'awaiting_pincode':
        user_states[from_number]['data']['pincode'] = msg_body
        user_states[from_number]['state'] = 'awaiting_password_register'
        send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]['ask_password'])
        return 'OK', 200

    if state == 'awaiting_password_register':
        d = user_states[from_number]['data']
        d.update(username=from_number, phone_number=from_number, password=msg_body)
        if register_farmer_api(d):
            login_resp = login_farmer_api(from_number, msg_body)
            if login_resp and login_resp.get('access'):
                user_states[from_number]['access_token'] = login_resp['access']
                user_states[from_number]['state'] = 'awaiting_category'
                send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]['reg_complete'])
                # show categories
                cat_text = "Select category:\n" + "\n".join(f"{k}. {v}" for k, v in CROP_CATEGORIES[lang].items())
                send_whatsapp_message(from_number, cat_text)
            else:
                send_whatsapp_message(from_number, "Registration OK but login failed; please say 'hi' to retry.")
        else:
            send_whatsapp_message(from_number, "Registration failed; please say 'hi' to start over.")
        return 'OK', 200

    # --- Login Flow for existing users ---
    if state == 'awaiting_password_login':
        login_resp = login_farmer_api(from_number, msg_body)
        if login_resp and login_resp.get('access'):
            user_states[from_number]['access_token'] = login_resp['access']
            user_states[from_number]['state'] = 'awaiting_category'
            send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]['welcome_back'])
            # now ask category right away
            cat_text = "What would you like to sell today? Select category:\n" + "\n".join(f"{k}. {v}" for k, v in CROP_CATEGORIES[lang].items())
            send_whatsapp_message(from_number, cat_text)
        else:
            send_whatsapp_message(from_number, "❌ Wrong password; please try again.")
        return 'OK', 200

    # --- Category, Product, Price, Quantity, More Crops ---
    if state == 'awaiting_category':
        if msg_body in CROP_CATEGORIES[lang]:
            cat_en = CROP_CATEGORIES['en'][msg_body]
            user_states[from_number]['temp_produce'] = {'category': cat_en}
            prods = PRODUCTS_BY_CATEGORY.get(cat_en, [])
            if prods:
                prod_text = "Select the crop:\n" + "\n".join(f"{i+1}. {p}" for i, p in enumerate(prods))
                send_whatsapp_message(from_number, prod_text)
                user_states[from_number]['state'] = 'awaiting_product'
            else:
                send_whatsapp_message(from_number, "No listed products; please type the crop name.")
                user_states[from_number]['state'] = 'awaiting_crop_name_manual'
        else:
            send_whatsapp_message(from_number, "Invalid choice; please select a category number.")
        return 'OK', 200

    if state == 'awaiting_product':
        try:
            idx = int(msg_body) - 1
            cat_en = user_states[from_number]['temp_produce']['category']
            crop = PRODUCTS_BY_CATEGORY[cat_en][idx]
            user_states[from_number]['temp_produce']['name'] = crop
            send_whatsapp_message(from_number, f"🔍 Fetching recent prices for {crop}...")
            st = user_states[from_number]['data'].get('state')
            prices = scrape_agmarknet_prices(st, crop)
            if prices:
                # you could add AI suggestion here...
                pass
            else:
                send_whatsapp_message(from_number, "📉 Couldn't find prices; please set your own.")
            user_states[from_number]['state'] = 'awaiting_price'
            send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]['ask_price'])
        except:
            send_whatsapp_message(from_number, "Invalid selection; please enter the number of the crop.")
        return 'OK', 200

    if state in ['awaiting_crop_name', 'awaiting_crop_name_manual']:
        user_states[from_number]['temp_produce'] = {'name': msg_body, 'category': 'Others'}
        send_whatsapp_message(from_number, f"Got it: {msg_body}. Now, please tell me the price per kg.")
        send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]['ask_price'])
        user_states[from_number]['state'] = 'awaiting_price'
        return 'OK', 200

    if state == 'awaiting_price':
        user_states[from_number]['temp_produce']['price_per_kg'] = msg_body
        user_states[from_number]['state'] = 'awaiting_quantity'
        send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]['ask_quantity'])
        return 'OK', 200

    if state == 'awaiting_quantity':
        user_states[from_number]['temp_produce']['quantity_kg'] = msg_body
        token = user_states[from_number].get('access_token')
        if token and add_produce_api(user_states[from_number]['temp_produce'], token):
            send_whatsapp_message(from_number, "✅ Your produce has been listed successfully!")
            send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]['ask_more_crops'])
            user_states[from_number]['state'] = 'awaiting_more_crops'
        else:
            send_whatsapp_message(from_number, "❌ Failed to save your produce. Please try again later.")
            user_states[from_number]['state'] = 'conversation_over'
        return 'OK', 200

    if state == 'awaiting_more_crops':
        if cmd in ['yes', 'y', '1', 'हाँ', 'हां']:
            user_states[from_number]['state'] = 'awaiting_category'
            cat_text = "Select next category:\n" + "\n".join(f"{k}. {v}" for k, v in CROP_CATEGORIES[lang].items())
            send_whatsapp_message(from_number, cat_text)
        else:
            send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]['thank_you'])
            user_states[from_number]['state'] = 'conversation_over'
        return 'OK', 200

    if cmd == 'thank you':
        send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]['thank_you'])
        user_states[from_number]['state'] = 'final'
        return 'OK', 200

    return 'OK', 200

@app.route('/notify-farmer', methods=['POST'])
def notify_farmer():
    data = request.json
    phone = data.get('phone_number')
    items = data.get('items', [])
    if not phone or not items:
        return jsonify({"error": "Invalid data"}), 400
    lang = user_states.get(phone, {}).get('language', 'en')
    lines, audios = [], []
    header = "🎉 *New Order!*" if lang=='en' else "🎉 *नया ऑर्डर!*"
    lines.append(header)
    for item in items:
        if lang=='hi':
            lines.append(f"👉 फसल: *{item['produce']}* | ✅ बिका: *{item['quantity_bought']}* किलो | 📦 बचा: *{item['remaining_stock']}* किलो")
            audios.append(f"{item['produce']} बिक गया है, {item['quantity_bought']} किलो, बचे {item['remaining_stock']} किलो।")
        else:
            lines.append(f"👉 Crop: *{item['produce']}* | ✅ Sold: *{item['quantity_bought']}* kg | 📦 Left: *{item['remaining_stock']}* kg")
            audios.append(f"{item['quantity_bought']} kilograms of your {item['produce']} sold, {item['remaining_stock']} kg left.")
    send_whatsapp_message(phone, "\n".join(lines))
    # send audio notification if needed...
    return jsonify({"status":"notification sent"}), 200

@app.route('/static/audio/<filename>')
def serve_audio(filename):
    return send_from_directory('static/audio', filename)

if __name__ == '__main__':
    os.makedirs('static/audio', exist_ok=True)
    app.run(host='0.0.0.0', port=5000, debug=True)
