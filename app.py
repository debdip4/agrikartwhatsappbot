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


# --- In-memory database for hackathon prototype ---
user_states = {}

# --- Dictionary to hold all your public audio file URLs ---
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
        "no_price_data": "https://raw.githubusercontent.com/debdip4/agrikartwhatsappbot/main/Audio_files/en_no_price_data.mp3",
        "ask_crop": "https://raw.githubusercontent.com/debdip4/agrikartwhatsappbot/main/Audio_files/en_ask_crop.mp3", # Assuming new audio file
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
        "no_price_data": "https://raw.githubusercontent.com/debdip4/agrikartwhatsappbot/main/Audio_files/hi_no_price_data.mp3",
        "ask_crop": "https://raw.githubusercontent.com/debdip4/agrikartwhatsappbot/main/Audio_files/hi_ask_crop.mp3", # Assuming new audio file
    }
}


def get_agmarknet_prices(commodity_name: str, state_name: str):
    """Scrapes agricultural commodity prices from agmarknet.gov.in."""
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = None
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        url = "https://agmarknet.gov.in/SearchCmmMkt.aspx"
        driver.get(url)
        driver.set_page_load_timeout(40)

        Select(driver.find_element(By.ID, "ddlCommodity")).select_by_visible_text(commodity_name)
        Select(driver.find_element(By.ID, "ddlState")).select_by_visible_text(state_name)
        driver.find_element(By.ID, "btnGo").click()

        wait = WebDriverWait(driver, 30)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#cphBody_GridPriceData tbody tr")))

        table_html = driver.find_element(By.ID, "cphBody_GridPriceData").get_attribute("outerHTML")
        df_list = pd.read_html(StringIO(table_html))
        
        if not df_list:
            print("Scraping failed: No table found.")
            return None
            
        df = df_list[0]
        if "No Data Found" in df.to_string():
            print(f"No data found on Agmarknet for {commodity_name} in {state_name}")
            return None
        return df
    except Exception as e:
        print(f"An error occurred during scraping: {e}")
        return None
    finally:
        if driver:
            driver.quit()


def analyze_price_data(price_df: pd.DataFrame):
    """Returns basic statistics for price suggestion."""
    if price_df is None or price_df.empty:
        return {"error": "Price data is not available."}

    price_col = "Modal Price (Rs./Quintal)"
    if price_col not in price_df.columns:
        return {"error": "Modal Price column not found."}
        
    modal_prices = pd.to_numeric(price_df[price_col], errors="coerce").dropna()
    
    if modal_prices.empty:
        return {"error": "No valid modal prices found to analyze."}

    return {
        "market_count": len(modal_prices),
        "min_price": modal_prices.min(),
        "max_price": modal_prices.max(),
        "avg_price": round(modal_prices.mean(), 2),
    }

def send_whatsapp_message(to: str, msg: str):
    """Sends a text message via WhatsApp API."""
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    payload = {"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": msg}}
    try:
        requests.post(url, headers=headers, json=payload, timeout=10).raise_for_status()
        print(f"Message sent to {to}")
    except requests.exceptions.RequestException as e:
        print(f"Error sending message to {to}: {e}")

def send_whatsapp_audio(to: str, audio_link: str):
    """Sends an audio message via WhatsApp API."""
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    payload = {"messaging_product": "whatsapp", "to": to, "type": "audio", "audio": {"link": audio_link}}
    try:
        requests.post(url, headers=headers, json=payload, timeout=10).raise_for_status()
        print(f"Audio sent to {to}: {audio_link}")
    except requests.exceptions.RequestException as e:
        print(f"Error sending audio to {to}: {e}")

def check_farmer_exists(phone_number):
    # This is a mock function. Replace with your actual API call.
    # For testing, we can check if the phone number exists in our in-memory user_states
    # and if they have completed registration (i.e., have a password).
    return phone_number in user_states and "password" in user_states[phone_number].get("data", {})


def register_farmer_api(user_data):
    url = f"{API_BASE_URL}/api/v1/auth/signup/farmer/"
    payload = {
        "username": user_data.get("username"),
        "password": user_data.get("password"),
        "email": f"{user_data.get('username')}@agrikart.ai",
        "phone_number": user_data.get("phone_number"),
        "name": user_data.get("name"),
        "address": user_data.get("address"),
        "pincode": user_data.get("pincode") # Added pincode
    }
    try:
        res = requests.post(url, json=payload, timeout=20)
        res.raise_for_status()
        return res.json()
    except Exception as e:
        print(f"Error in register_farmer_api: {e}")
        return None

def login_farmer_api(username, password):
    url = f"{API_BASE_URL}/api/v1/auth/token/"
    payload = {"username": username, "password": password}
    try:
        res = requests.post(url, json=payload, timeout=20)
        res.raise_for_status()
        return res.json()
    except Exception as e:
        print(f"Error in login_farmer_api: {e}")
        return None

def add_produce_api(produce_data, access_token):
    url = f"{API_BASE_URL}/api/v1/produce/"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    payload = {
        "name": produce_data["name"],
        "price": float(produce_data["price_per_kg"]),
        "quantity": float(produce_data["quantity_kg"]),
        "category": "Others",
    }
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=20)
        res.raise_for_status()
        return res.json()
    except Exception as e:
        print(f"Error in add_produce_api: {e}")
        return None


def generate_tts_elevenlabs(text, lang="en"):
    """Generates TTS audio and returns a public URL."""
    try:
        eleven_api_key = os.getenv("ELEVENLABS_API_KEY")
        voice_id = "EXAVITQu4vr4xnSDxMaL"
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?optimize_streaming_latency=0"
        
        headers = {"Accept": "audio/mpeg", "Content-Type": "application/json", "xi-api-key": eleven_api_key}
        data = {"text": text, "model_id": "eleven_multilingual_v2", "voice_settings": {"stability": 0.55, "similarity_boost": 0.75}}

        response = requests.post(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()

        filename = f"{int(time.time())}_{lang}.mp3"
        path = os.path.join("static/audio", filename)
        with open(path, "wb") as f:
            f.write(response.content)
            
        if not PUBLIC_URL:
            print("WARNING: PUBLIC_URL environment variable not set.")
            return None
        return f"{PUBLIC_URL}/static/audio/{filename}"

    except Exception as e:
        print(f"TTS generation error: {e}")
        return None


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

        if from_number not in user_states:
            user_states[from_number] = {"data": {}, "language": "en"}

        current_state = user_states[from_number].get("state")
        lang = user_states[from_number].get("language", "en")

        # --- REWORKED STATE MACHINE ---
        
        if command in ["hi", "hello", "नमस्ते"] and not current_state:
            if check_farmer_exists(from_number):
                user_states[from_number]["state"] = "awaiting_login_password"
                send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]["welcome_back"])
                send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]["ask_loginpassword"])
            else:
                user_states[from_number]["state"] = "awaiting_language_choice"
                send_whatsapp_audio(from_number, AUDIO_CLIPS["welcome"])
                send_whatsapp_message(from_number, "Please select your language:\n1. English\n2. हिन्दी")
            return "OK", 200

        # --- LOGIN FLOW ---
        if current_state == "awaiting_login_password":
            password = msg_body
            # Mock login: Use stored password. Replace with your actual login API
            if user_states[from_number].get("data", {}).get("password") == password:
                send_whatsapp_message(from_number, "✅ Login successful!")
                # Transition to state selection
                state_list_message = "Please select your state by replying with the number:\n"
                state_list_message += "\n".join([f"{num}. {name}" for num, name in STATES.items()])
                send_whatsapp_message(from_number, state_list_message)
                user_states[from_number]["state"] = "awaiting_state_selection"
            else:
                send_whatsapp_message(from_number, "❌ Incorrect password. Please try again.")
                send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]["ask_loginpassword"])

        # --- REGISTRATION FLOW ---
        elif current_state == "awaiting_language_choice":
            lang = "hi" if "2" in command else "en"
            user_states[from_number]["language"] = lang
            user_states[from_number]["state"] = "awaiting_name"
            send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]["ask_name"])

        elif current_state == "awaiting_name":
            user_states[from_number]["data"]["name"] = msg_body
            user_states[from_number]["state"] = "awaiting_address"
            send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]["ask_address"])

        elif current_state == "awaiting_address":
            user_states[from_number]["data"]["address"] = msg_body
            user_states[from_number]["state"] = "awaiting_pincode"
            send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]["ask_pincode"])

        elif current_state == "awaiting_pincode":
            user_states[from_number]["data"]["pincode"] = msg_body
            user_states[from_number]["state"] = "awaiting_password"
            send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]["ask_password"])
        
        elif current_state == "awaiting_password":
            user_states[from_number]["data"]["password"] = msg_body
            user_states[from_number]["data"]["username"] = from_number
            user_states[from_number]["data"]["phone_number"] = from_number
            
            # Mocking successful registration for testing
            send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]["reg_complete"])
            state_list_message = "Please select your state by replying with the number:\n"
            state_list_message += "\n".join([f"{num}. {name}" for num, name in STATES.items()])
            send_whatsapp_message(from_number, state_list_message)
            user_states[from_number]["state"] = "awaiting_state_selection"

        # --- PRODUCE LISTING FLOW (POST LOGIN/REG) ---
        elif current_state == "awaiting_state_selection":
            state_name = STATES.get(command)
            if not state_name:
                send_whatsapp_message(from_number, "❌ Invalid selection. Please reply with a valid number from the list.")
            else:
                user_states[from_number]["temp_produce"] = {"state": state_name}
                user_states[from_number]["state"] = "awaiting_crop_name"
                send_whatsapp_message(from_number, f"✅ State set to: {state_name}")
                send_whatsapp_audio(from_number, AUDIO_CLIPS[lang].get("ask_crop", AUDIO_CLIPS["en"]["ask_crop"])) # Fallback to EN audio

        elif current_state == "awaiting_crop_name":
            crop_name = msg_body.title()
            state_name = user_states[from_number]["temp_produce"]["state"]
            user_states[from_number]["temp_produce"]["name"] = crop_name
            
            send_whatsapp_message(from_number, f"⏳ Searching for {crop_name} prices in {state_name}...")
            price_df = get_agmarknet_prices(crop_name, state_name)
            price_summary = analyze_price_data(price_df)

            if "error" in price_summary:
                suggestion_text = "Sorry, I could not find price data for this crop. Please enter your desired price per kg."
                send_whatsapp_message(from_number, suggestion_text)
                send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]["no_price_data"])
            else:
                suggestion_text = (
                    f"📈 Based on {price_summary['market_count']} markets in {state_name}, the average price for {crop_name} is "
                    f"₹{price_summary['avg_price']} per Quintal (100 kg).\n\n"
                    "Now, please tell me your desired selling price per kg."
                )
                send_whatsapp_message(from_number, suggestion_text)
                audio_url = generate_tts_elevenlabs(suggestion_text, lang)
                if audio_url: send_whatsapp_audio(from_number, audio_url)
            
            user_states[from_number]["state"] = "awaiting_price"

        elif current_state == "awaiting_price":
            try:
                price = float(msg_body)
                user_states[from_number]["temp_produce"]["price_per_kg"] = price
                user_states[from_number]["state"] = "awaiting_quantity"
                send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]["ask_quantity"])
            except ValueError:
                send_whatsapp_message(from_number, "❌ Please enter a valid number for the price.")

        elif current_state == "awaiting_quantity":
            try:
                quantity = float(msg_body)
                user_states[from_number]["temp_produce"]["quantity_kg"] = quantity
                
                # Mocking adding produce for testing
                send_whatsapp_message(from_number, "✅ Your produce has been listed successfully!")
                send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]["ask_more_crops"])
                user_states[from_number]["state"] = "awaiting_more_crops"

            except ValueError:
                send_whatsapp_message(from_number, "❌ Please enter a valid number for the quantity.")

        elif current_state == "awaiting_more_crops":
            if command in ["yes", "y", "ok", "1", "हाँ", "हां"]:
                state_list_message = "Please select your state by replying with the number:\n"
                state_list_message += "\n".join([f"{num}. {name}" for num, name in STATES.items()])
                send_whatsapp_message(from_number, state_list_message)
                user_states[from_number]["state"] = "awaiting_state_selection"
            else:
                send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]["thank_you"])
                user_states[from_number]["state"] = "conversation_over"

        elif current_state == "conversation_over":
            send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]["closing"])
            del user_states[from_number]["state"] # Reset state for next time

    except (IndexError, KeyError):
        pass # Ignore non-message webhooks
    except Exception as e:
        print(f"Global webhook processing error: {e}")

    return "OK", 200


@app.route("/notify-farmer", methods=["POST"])
def notify_farmer():
    try:
        data = request.json
        phone = data.get("phone_number")
        items = data.get("items", [])

        if not phone or not items:
            return jsonify({"error": "Invalid data"}), 400

        user_lang = user_states.get(phone, {}).get("language", "en")
        
        text_message_lines, audio_message_parts = [], []

        if user_lang == 'hi':
            text_message_lines.append("🎉 *नया ऑर्डर!*")
            audio_message_parts.append("नमस्ते, आपको एक नया ऑर्डर मिला है।")
        else:
            text_message_lines.append("🎉 *New Order!*")
            audio_message_parts.append("Hello, you have a new order.")

        for item in items:
            produce_name = item.get("produce", "N/A")
            quantity_bought = item.get("quantity_bought", 0)
            remaining_stock = item.get("remaining_stock", 0)

            if user_lang == 'hi':
                text_message_lines.append(f"👉 फसल: *{produce_name}*\n✅ बिका: *{quantity_bought}* किलो\n📦 बचा है: *{remaining_stock}* किलो")
                audio_message_parts.append(f"{quantity_bought} किलो {produce_name} बिक गया है, और अब {remaining_stock} किलो बचा है।")
            else:
                text_message_lines.append(f"👉 Crop: *{produce_name}*\n✅ Sold: *{quantity_bought}* kg\n📦 Left: *{remaining_stock}* kg")
                audio_message_parts.append(f"{quantity_bought} kilograms of {produce_name} has been sold. You have {remaining_stock} kilograms remaining.")

        send_whatsapp_message(phone, "\n\n".join(text_message_lines))
        
        audio_url = generate_tts_elevenlabs(" ".join(audio_message_parts), user_lang)
        if audio_url:
            send_whatsapp_audio(phone, audio_url)

        return jsonify({"status": "notification_sent"}), 200
        
    except Exception as e:
        print(f"Error in /notify-farmer endpoint: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    if not os.path.exists("static/audio"):
        os.makedirs("static/audio")
    print("WhatsApp Bot Running...")
    app.run(port=5000, debug=True)
