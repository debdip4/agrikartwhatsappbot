import os
import json
import requests
import time
import pandas as pd
from flask import Flask, request, jsonify
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
PHONE_NUMBER_ID = os.getenv('WHATSAPP_PHONE_NUMBER_ID') # Using the name you specified
API_BASE_URL = os.getenv('BACKEND_API_BASE_URL')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY')

# --- In-memory database for prototype ---
# In a production environment, consider using Redis or a proper database for this
user_states = {}

# --- Audio and Crop Data ---
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

# This list should be expanded with more products for each category
PRODUCTS_BY_CATEGORY = {
    "Fruits": ["Apple", "Mango", "Banana", "Grapes", "Orange", "Pineapple"],
    "Vegetables": ["Potato", "Onion", "Tomato", "Carrot", "Cauliflower", "Brinjal"],
    "Organic": ["Organic Honey", "Organic Tea", "Organic Rice"],
    "Dairy & Eggs": ["Milk", "Cheese", "Butter", "Eggs"],
    "Grains & Pulses": ["Wheat", "Rice", "Maize", "Arhar Dal", "Moong Dal"],
}

# Mapping of states for the Agmarknet portal
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


# --- Selenium Web Scraper for Agmarknet ---
def setup_driver():
    """Sets up the Selenium WebDriver for Chrome in headless mode."""
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    # The Dockerfile sets the CHROME_BIN env var, which Selenium should pick up automatically.
    driver = webdriver.Chrome(options=chrome_options)
    return driver

def scrape_agmarknet_prices(state, commodity):
    """Scrapes commodity prices from the Agmarknet portal."""
    driver = setup_driver()
    try:
        url = "https://agmarknet.gov.in/PriceAndArrivals/DatewiseCommodityReport.aspx"
        driver.get(url)
        print(f"Scraping for State: {state}, Commodity: {commodity}")

        # Wait for elements to be loaded
        wait = WebDriverWait(driver, 10)

        # Select State
        state_code = AGMARKNET_STATES.get(state)
        if not state_code:
            print(f"Error: Invalid state '{state}' provided.")
            return []
        Select(wait.until(EC.presence_of_element_located((By.ID, "cphBody_cboState")))).select_by_value(state_code)

        # Select Commodity
        # We add a small delay to let the commodity list populate based on the state
        time.sleep(2)
        Select(wait.until(EC.presence_of_element_located((By.ID, "cphBody_cboCommodity")))).select_by_visible_text(commodity)

        # Click the 'Go' button
        driver.find_element(By.ID, "cphBody_btnSubmit").click()

        # Wait for the results table to appear
        wait.until(EC.presence_of_element_located((By.ID, "cphBody_gridRecords")))
        
        # Scrape the table using Pandas
        html = driver.page_source
        tables = pd.read_html(html, attrs={'id': 'cphBody_gridRecords'})
        
        if tables:
            df = tables[0]
            # Keep only relevant columns and clean up data
            df = df[['Market Name', 'Min Price (Rs./Quintal)', 'Max Price (Rs./Quintal)', 'Modal Price (Rs./Quintal)']]
            # Convert Quintal prices to per Kg
            for col in ['Min Price (Rs./Quintal)', 'Max Price (Rs./Quintal)', 'Modal Price (Rs./Quintal)']:
                 df[col.replace('Quintal', 'Kg')] = pd.to_numeric(df[col], errors='coerce') / 100
            
            # Extract modal prices, dropping any invalid entries
            prices = df['Modal Price (Rs./Kg)'].dropna().tolist()
            return prices
        return []

    except TimeoutException:
        print("Scraping timed out. The page or an element took too long to load.")
        return []
    except Exception as e:
        print(f"An error occurred during scraping: {e}")
        return []
    finally:
        driver.quit()

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
    # Combine address, state, and pincode into a single address string
    full_address = f"{user_data.get('address', '')}, {user_data.get('state', '')} - {user_data.get('pincode', '')}"
    payload = {
        "username": user_data['username'],
        "password": user_data['password'],
        "email": f"{user_data['username']}@agrikart.ai", # Create a dummy email
        "phone_number": user_data['phone_number'],
        "name": user_data['name'],
        "address": full_address
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
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "name": produce_data['name'],
        "price": float(produce_data['price_per_kg']),
        "quantity": float(produce_data['quantity_kg']),
        "category": produce_data.get('category', 'Others') # Use selected category
    }
    try:
        res = requests.post(url, headers=headers, json=payload)
        res.raise_for_status()
        return res.json()
    except Exception as e:
        print(f"Error in add_produce_api: {e}")
        return None

# --- Messaging & AI Helpers ---
def send_whatsapp_message(to, msg):
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    payload = {"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": msg}}
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
    except Exception as e:
        print(f"Error sending text message: {e}")

def send_whatsapp_audio(to, url_link):
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    payload = {"messaging_product": "whatsapp", "to": to, "type": "audio", "audio": {"link": url_link}}
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
    except Exception as e:
        print(f"Error sending audio message: {e}")

def query_ai_for_price_suggestion(crop_name, prices, lang):
    if not prices:
        return "Not enough data to suggest a price." if lang == 'en' else "मूल्य सुझाने के लिए पर्याप्त डेटा नहीं है।"
        
    price_list_str = ', '.join(f"₹{p:.2f}" for p in prices)
    prompt = f"""
    You are an agricultural assistant for farmers in India.
    A farmer wants to sell "{crop_name}".
    Current market prices for this crop in their region are: {price_list_str} per kg.
    Suggest a fair selling price per kg.
    Your reply must be a single, short, encouraging sentence.
    Example: "A good price would be around ₹X/kg, as similar prices are common in the market."
    {"Reply in simple Hindi." if lang == "hi" else "Reply in simple English."}
    """
    try:
        res = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "deepseek/deepseek-r1-0528-qwen3-8b:free", # Using a free model from OpenRouter
                "messages": [{"role": "user", "content": prompt}]
            }
        )
        res.raise_for_status()
        return res.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"❌ AI suggestion error: {e}")
        avg_price = round(sum(prices) / len(prices), 2)
        return f"Recommended price is around ₹{avg_price}/kg." if lang == 'en' else f"अनुशंसित मूल्य लगभग ₹{avg_price}/किग्रा है।"

def generate_tts_elevenlabs(text, lang='en'):
    if not ELEVENLABS_API_KEY:
        print("❌ ElevenLabs API key not set. Skipping TTS generation.")
        return None
    try:
        # A good generic voice for multilingual content
        VOICE_ID = "21m00Tcm4TlvDq8ikWAM"
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": ELEVENLABS_API_KEY
        }
        response = requests.post(url, headers=headers, json={
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}
        }, timeout=20)

        if response.status_code == 200:
            filename = f"{int(time.time())}.mp3"
            # In a container, write to a designated volume or a known path
            path = os.path.join("static/audio", filename)
            with open(path, 'wb') as f:
                f.write(response.content)
            # This URL needs to be publicly accessible. Using ngrok for local dev is fine.
            # For TrueFoundry, you might need to serve static files or upload to a cloud storage (like S3).
            # The current approach assumes the Flask app serves the files.
            base_url = os.getenv("PUBLIC_URL", "") # e.g., your ngrok or TrueFoundry service URL
            return f"{base_url}/static/audio/{filename}"
        else:
            print(f"❌ ElevenLabs error: {response.status_code}, {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error generating audio via ElevenLabs: {e}")
        return None


# --- Main Webhook Logic ---
@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        if request.args.get('hub.mode') == 'subscribe' and request.args.get('hub.verify_token') == VERIFY_TOKEN:
            return request.args.get('hub.challenge'), 200
        return 'Unauthorized', 403

    data = request.get_json()
    try:
        # Standard WhatsApp webhook parsing
        entry = data.get("entry", [])[0]
        change = entry.get("changes", [])[0]
        value = change.get("value", {})
        messages = value.get("messages")

        if not messages:
            return 'OK', 200 # Ignore non-message events

        message = messages[0]
        from_number = message['from']
        msg_body = message.get('text', {}).get('body', '').strip()
        command = msg_body.lower()
        print(f"📩 Message from {from_number}: '{msg_body}'")

        # Initialize state for new users
        if from_number not in user_states:
            user_states[from_number] = {"data": {}, "state": None}

        current_state = user_states[from_number].get("state")
        print(f"🔁 Current state for {from_number}: {current_state}")
        
        # --- Start of Conversation Flow ---
        if command in ['hi', 'hello', 'नमस्ते']:
            if check_farmer_exists(from_number):
                user_states[from_number]['state'] = 'awaiting_lang_after_exists'
            else:
                user_states[from_number]['state'] = 'awaiting_language_choice'
            send_whatsapp_audio(from_number, AUDIO_CLIPS['welcome'])
            return 'OK', 200

        # --- State Machine ---
        lang = user_states[from_number].get('language', 'en') # Default to 'en' if not set

        if current_state in ['awaiting_language_choice', 'awaiting_lang_after_exists']:
            is_existing_user = (current_state == 'awaiting_lang_after_exists')
            lang = 'hi' if '2' in command else 'en'
            user_states[from_number]['language'] = lang
            
            if is_existing_user:
                user_states[from_number]['state'] = 'awaiting_password_login'
                send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]['ask_loginpassword'])
            else:
                user_states[from_number]['state'] = 'awaiting_name'
                send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]['ask_name'])

        elif current_state == 'awaiting_name':
            user_states[from_number]['data']['name'] = msg_body
            user_states[from_number]['state'] = 'awaiting_address'
            send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]['ask_address'])

        elif current_state == 'awaiting_address':
            user_states[from_number]['data']['address'] = msg_body
            user_states[from_number]['state'] = 'awaiting_state'
            # Ask for state by sending a list
            state_list_text = "Please select your state by replying with the number:\n" + "\n".join([f"{i+1}. {s}" for i, s in enumerate(AGMARKNET_STATES.keys())])
            send_whatsapp_message(from_number, state_list_text)
            send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]['ask_state'])

        elif current_state == 'awaiting_state':
            try:
                state_index = int(msg_body) - 1
                if 0 <= state_index < len(AGMARKNET_STATES):
                    state_name = list(AGMARKNET_STATES.keys())[state_index]
                    user_states[from_number]['data']['state'] = state_name
                    user_states[from_number]['state'] = 'awaiting_pincode'
                    send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]['ask_pincode'])
                else:
                    send_whatsapp_message(from_number, "Invalid number. Please try again.")
            except ValueError:
                send_whatsapp_message(from_number, "Please reply with a number only.")

        elif current_state == 'awaiting_pincode':
            user_states[from_number]['data']['pincode'] = msg_body
            user_states[from_number]['state'] = 'awaiting_password_register'
            send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]['ask_password'])

        elif current_state == 'awaiting_password_register':
            user_states[from_number]['data']['password'] = msg_body
            user_states[from_number]['data']['username'] = from_number
            user_states[from_number]['data']['phone_number'] = from_number
            
            if register_farmer_api(user_states[from_number]['data']):
                login_resp = login_farmer_api(from_number, msg_body)
                if login_resp and login_resp.get('access'):
                    user_states[from_number]['access_token'] = login_resp['access']
                    user_states[from_number]['state'] = 'awaiting_category'
                    send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]['reg_complete'])
                    # Ask to select category
                    category_text = (CROP_CATEGORIES['hi']['title'] if lang == 'hi' else CROP_CATEGORIES['en']['title']) + "\n" + "\n".join([f"{k}. {v}" for k,v in CROP_CATEGORIES[lang].items() if k != 'title'])
                    send_whatsapp_message(from_number, category_text)
                else:
                    send_whatsapp_message(from_number, "❌ Registration successful, but login failed. Please type 'hi' to try again.")
            else:
                send_whatsapp_message(from_number, "❌ Registration failed. Please type 'hi' to start over.")
        
        elif current_state == 'awaiting_password_login':
            password = msg_body
            login_resp = login_farmer_api(from_number, password)
            if login_resp and login_resp.get('access'):
                user_states[from_number]['access_token'] = login_resp['access']
                user_states[from_number]['state'] = 'awaiting_crop_name'
                send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]['welcome_back'])
                send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]['next_crop'])
            else:
                send_whatsapp_message(from_number, "❌ Wrong password. Please try again.")

        elif current_state == 'awaiting_category':
            category_choice = msg_body
            if category_choice in CROP_CATEGORIES[lang]:
                # Store the English category name for backend API
                selected_category_en = CROP_CATEGORIES['en'][category_choice]
                user_states[from_number]['temp_produce'] = {'category': selected_category_en}
                
                products = PRODUCTS_BY_CATEGORY.get(selected_category_en, [])
                if products:
                    product_list_text = "Select the crop you want to list (reply with the number):\n" + "\n".join([f"{i+1}. {p}" for i,p in enumerate(products)])
                    send_whatsapp_message(from_number, product_list_text)
                    user_states[from_number]['state'] = 'awaiting_product'
                else:
                    send_whatsapp_message(from_number, "No products found for this category. Please type the crop name directly.")
                    user_states[from_number]['state'] = 'awaiting_crop_name_manual'
            else:
                 send_whatsapp_message(from_number, "Invalid selection. Please choose a number from the list.")

        elif current_state == 'awaiting_product':
            try:
                product_index = int(msg_body) - 1
                selected_category_en = user_states[from_number]['temp_produce']['category']
                products = PRODUCTS_BY_CATEGORY.get(selected_category_en, [])

                if 0 <= product_index < len(products):
                    crop_name = products[product_index]
                    user_states[from_number]['temp_produce']['name'] = crop_name
                    
                    # --- Price Scraping and Suggestion ---
                    send_whatsapp_message(from_number, f"🔍 Searching for latest prices of {crop_name}. Please wait...")
                    farmer_state = user_states[from_number].get('data', {}).get('state')
                    if farmer_state:
                        prices = scrape_agmarknet_prices(farmer_state, crop_name)
                        print(f"👀 Scraped prices for '{crop_name}': {prices}")
                        
                        if prices:
                            ai_reply = query_ai_for_price_suggestion(crop_name, prices, lang)
                            send_whatsapp_message(from_number, f"🤖 Suggestion:\n{ai_reply}")
                            audio_url = generate_tts_elevenlabs(ai_reply, lang)
                            if audio_url:
                                send_whatsapp_audio(from_number, audio_url)
                        else:
                            send_whatsapp_message(from_number, "📉 Could not find recent price data for your state. Please set your own price.")
                    else:
                        send_whatsapp_message(from_number, "State information not found. Cannot fetch price suggestions.")

                    # Proceed to ask for price
                    user_states[from_number]['state'] = 'awaiting_price'
                    send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]['ask_price'])
                else:
                    send_whatsapp_message(from_number, "Invalid number. Please try again.")
            except (ValueError, KeyError):
                send_whatsapp_message(from_number, "Please reply with a number from the list.")
        
        elif current_state == 'awaiting_crop_name' or current_state == 'awaiting_crop_name_manual':
             # This state is for when user adds more crops or when product list fails
            crop_name = msg_body.strip()
            # We assume a general category if entered manually
            user_states[from_number]['temp_produce'] = {'name': crop_name, 'category': 'Others'}
            # --- You could optionally trigger the price scraping here as well ---
            send_whatsapp_message(from_number, f"Got it: {crop_name}. Now, please tell me the price.")
            send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]['ask_price'])
            user_states[from_number]['state'] = 'awaiting_price'

        elif current_state == 'awaiting_price':
            user_states[from_number]['temp_produce']['price_per_kg'] = msg_body
            user_states[from_number]['state'] = 'awaiting_quantity'
            send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]['ask_quantity'])

        elif current_state == 'awaiting_quantity':
            user_states[from_number]['temp_produce']['quantity_kg'] = msg_body
            token = user_states[from_number].get('access_token')
            if token and add_produce_api(user_states[from_number]['temp_produce'], token):
                send_whatsapp_message(from_number, "✅ Your produce has been listed successfully!")
                send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]['ask_more_crops'])
                user_states[from_number]['state'] = 'awaiting_more_crops'
            else:
                send_whatsapp_message(from_number, "❌ Failed to save your produce. Please try again later.")
                user_states[from_number]['state'] = 'conversation_over' # End flow on failure

        elif current_state == 'awaiting_more_crops':
            if command in ['yes', 'y', '1', 'हाँ', 'हां']:
                send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]['next_crop'])
                # Ask for category again for the next crop
                user_states[from_number]['state'] = 'awaiting_category'
                category_text = "\n".join([f"{k}. {v}" for k,v in CROP_CATEGORIES[lang].items() if k != 'title'])
                send_whatsapp_message(from_number, category_text)
            else:
                send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]['thank_you'])
                user_states[from_number]['state'] = 'conversation_over'
        
        elif msg_body.lower() == 'thank you': # Handle explicit "thank you" to close conversation
             send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]['closing'])
             user_states[from_number]['state'] = 'final' # A terminal state

    except Exception as e:
        print(f"❌ Unhandled Error in webhook: {e}")
        # Consider logging the full traceback for debugging
        import traceback
        traceback.print_exc()

    return 'OK', 200

# --- Notification Endpoint ---
@app.route('/notify-farmer', methods=['POST'])
def notify_farmer():
    try:
        data = request.json
        phone = data.get('phone_number')
        items = data.get('items', [])

        if not phone or not items:
            return jsonify({"error": "Invalid data, 'phone_number' and 'items' are required."}), 400

        user_lang = user_states.get(phone, {}).get('language', 'en')
        message_lines = []
        audio_parts = []

        if user_lang == 'hi':
            message_lines.append("🎉 *नया ऑर्डर!*")
            audio_parts.append("नमस्ते, आपके लिए एक नया ऑर्डर आया है!")
        else:
            message_lines.append("🎉 *New Order!*")
            audio_parts.append("Hello, you have a new order!")

        for item in items:
            if user_lang == 'hi':
                message_lines.append(f"👉 फसल: *{item['produce']}*\n✅ बिका: *{item['quantity_bought']}* किलो\n📦 बचा है: *{item['remaining_stock']}* किलो")
                audio_parts.append(f"{item['produce']}, {item['quantity_bought']} किलो बिक गया है, और {item['remaining_stock']} किलो बचा है।")
            else:
                message_lines.append(f"👉 Crop: *{item['produce']}*\n✅ Sold: *{item['quantity_bought']}* kg\n📦 Left: *{item['remaining_stock']}* kg")
                audio_parts.append(f"{item['quantity_bought']} kilograms of your {item['produce']} has been sold. You have {item['remaining_stock']} kilograms remaining.")

        send_whatsapp_message(phone, "\n\n".join(message_lines))
        
        audio_url = generate_tts_elevenlabs(" ".join(audio_parts), user_lang)
        if audio_url:
            send_whatsapp_audio(phone, audio_url)

        return jsonify({"status": "notification sent"}), 200
    except Exception as e:
        print(f"❌ Error in /notify-farmer: {e}")
        return jsonify({"error": str(e)}), 500

# Endpoint to serve static audio files generated by ElevenLabs
@app.route('/static/audio/<filename>')
def serve_audio(filename):
    return send_from_directory('static/audio', filename)

if __name__ == '__main__':
    # Create static/audio directory if it doesn't exist
    if not os.path.exists('static/audio'):
        os.makedirs('static/audio')
    print("🚀 WhatsApp Bot Running...")
    # Use Gunicorn in production as specified in your Dockerfile.
    # For local development, this is fine:
    app.run(host='0.0.0.0', port=5000, debug=True)
