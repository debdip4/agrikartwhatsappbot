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
PUBLIC_URL = os.getenv("PUBLIC_URL") # IMPORTANT: Add your public URL (like ngrok or deployment URL) to .env

# --- In-memory database for hackathon prototype ---
user_states = {}

# --- Dictionary to hold all your public audio file URLs ---
AUDIO_CLIPS = {
    "welcome": "https://raw.githubusercontent.com/debdip4/agrikartwhatsappbot/main/Audio_files/welcome.mp3",
    "en": {
        "ask_name": "https://raw.githubusercontent.com/debdip4/agrikartwhatsappbot/main/Audio_files/en_ask_name.mp3",
        "ask_address": "https://raw.githubusercontent.com/debdip4/agrikartwhatsappbot/main/Audio_files/en_ask_address.mp3",
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
    },
    "hi": {
        "ask_name": "https://raw.githubusercontent.com/debdip4/agrikartwhatsappbot/main/Audio_files/hi_ask_name.mp3",
        "ask_address": "https://raw.githubusercontent.com/debdip4/agrikartwhatsappbot/main/Audio_files/hi_ask_address.mp3",
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
    }
}

# ---------------------------------------------------------------------------
#                  GOVERNMENT PRICE SCRAPER AND ANALYSER
# ---------------------------------------------------------------------------

def get_agmarknet_prices(commodity_name: str, state_name: str):
    """Scrapes agricultural commodity prices from agmarknet.gov.in."""
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = None
    try:
        # Use webdriver_manager to handle driver installation
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        url = "https://agmarknet.gov.in/SearchCmmMkt.aspx"
        driver.get(url)
        
        # Increased timeout for page load
        driver.set_page_load_timeout(40)

        Select(driver.find_element(By.ID, "ddlCommodity")).select_by_visible_text(commodity_name)
        Select(driver.find_element(By.ID, "ddlState")).select_by_visible_text(state_name)
        driver.find_element(By.ID, "btnGo").click()

        # Wait for the table to be present
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
        
    # Convert to numeric, coercing errors to NaN, then drop them
    modal_prices = pd.to_numeric(price_df[price_col], errors="coerce").dropna()
    
    if modal_prices.empty:
        return {"error": "No valid modal prices found to analyze."}

    return {
        "market_count": len(modal_prices),
        "min_price": modal_prices.min(),
        "max_price": modal_prices.max(),
        "avg_price": round(modal_prices.mean(), 2),
    }

# ---------------------------------------------------------------------------
#                         MESSAGING HELPERS
# ---------------------------------------------------------------------------

def send_whatsapp_message(to: str, msg: str):
    """Sends a text message via WhatsApp API."""
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    payload = {"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": msg}}
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        print(f"Message sent to {to}: {msg}")
    except requests.exceptions.RequestException as e:
        print(f"Error sending message to {to}: {e}")

def send_whatsapp_audio(to: str, audio_link: str):
    """Sends an audio message via WhatsApp API."""
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    payload = {"messaging_product": "whatsapp", "to": to, "type": "audio", "audio": {"link": audio_link}}
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        print(f"Audio sent to {to}: {audio_link}")
    except requests.exceptions.RequestException as e:
        print(f"Error sending audio to {to}: {e}")

# ---------------------------------------------------------------------------
#                  EXISTING BACKEND API HELPERS
# ---------------------------------------------------------------------------

def check_farmer_exists(phone_number):
    url = f"http://localhost:8000/api/v1/farmer/check/{phone_number}/"
    try:
        response = requests.get(url, timeout=15)
        return response.status_code == 200 and response.json().get("exists", False)
    except requests.exceptions.RequestException as e:
        print(f"ERROR checking farmer existence: {e}")
        return False

def register_farmer_api(user_data):
    url = f"{API_BASE_URL}/api/v1/auth/signup/farmer/"
    payload = {
        "username": user_data["username"],
        "password": user_data["password"],
        "email": f"{user_data['username']}@agrikart.ai",
        "phone_number": user_data["phone_number"],
        "name": user_data["name"],
        "address": user_data["address"],
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
        "category": "Others", # Default category
    }
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=20)
        res.raise_for_status()
        return res.json()
    except Exception as e:
        print(f"Error in add_produce_api: {e}")
        return None

# ---------------------------------------------------------------------------
#                       TEXT TO SPEECH WITH ELEVENLABS
# ---------------------------------------------------------------------------

def generate_tts_elevenlabs(text, lang="en", voice="Bella"):
    """Generates TTS audio and returns a public URL."""
    try:
        eleven_api_key = os.getenv("ELEVENLABS_API_KEY")
        voice_id = "EXAVITQu4vr4xnSDxMaL"  # Pre-defined voice ID
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?optimize_streaming_latency=0"
        
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": eleven_api_key,
        }
        
        data = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {"stability": 0.55, "similarity_boost": 0.75},
        }

        response = requests.post(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()

        # Save the audio file locally
        filename = f"{int(time.time())}_{lang}.mp3"
        path = os.path.join("static/audio", filename)
        with open(path, "wb") as f:
            f.write(response.content)
            
        # Construct the public URL for the saved file
        if not PUBLIC_URL:
            print("WARNING: PUBLIC_URL environment variable not set. Audio may not be accessible.")
            return None
        return f"{PUBLIC_URL}/static/audio/{filename}"

    except Exception as e:
        print(f"TTS generation error: {e}")
        return None

# ---------------------------------------------------------------------------
#                                   WEBHOOK
# ---------------------------------------------------------------------------

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        # Handle webhook verification
        if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.verify_token") == VERIFY_TOKEN:
            return request.args.get("hub.challenge"), 200
        return "Unauthorized", 403

    # Process incoming message
    data = request.get_json()
    try:
        message = data["entry"][0]["changes"][0]["value"]["messages"][0]
        from_number = message["from"]
        msg_body = message["text"]["body"].strip()
        command = msg_body.lower()

        # Initialize state for new user
        if from_number not in user_states:
            user_states[from_number] = {"data": {}, "language": "en"} # Default to English

        current_state = user_states[from_number].get("state")
        lang = user_states[from_number].get("language", "en")

        # --- STATE MACHINE ---
        
        # Start of conversation
        if command in ["hi", "hello", "नमस्ते"]:
            if check_farmer_exists(from_number):
                user_states[from_number]["state"] = "awaiting_lang_after_exists"
            else:
                user_states[from_number]["state"] = "awaiting_language_choice"
            send_whatsapp_audio(from_number, AUDIO_CLIPS["welcome"])
            send_whatsapp_message(from_number, "Please select your language:\n1. English\n2. हिन्दी")

        # Language selection for existing user
        elif current_state == "awaiting_lang_after_exists":
            lang = "hi" if "2" in command else "en"
            user_states[from_number]["language"] = lang
            send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]["ask_loginpassword"])
            user_states[from_number]["state"] = "awaiting_password"

        # Language selection for new user
        elif current_state == "awaiting_language_choice":
            lang = "hi" if "2" in command else "en"
            user_states[from_number]["language"] = lang
            user_states[from_number]["state"] = "awaiting_name"
            send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]["ask_name"])

        # Registration flow
        elif current_state == "awaiting_name":
            user_states[from_number]["data"]["name"] = msg_body
            user_states[from_number]["state"] = "awaiting_address"
            send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]["ask_address"])

        elif current_state == "awaiting_address":
            user_states[from_number]["data"]["address"] = msg_body
            user_states[from_number]["state"] = "awaiting_password"
            send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]["ask_password"])

        # Password handling (for both login and registration)
        elif current_state == "awaiting_password":
            password = msg_body
            user_states[from_number]["data"]["password"] = password
            user_states[from_number]["data"]["username"] = from_number
            user_states[from_number]["data"]["phone_number"] = from_number

            if check_farmer_exists(from_number):
                # Try to log in
                login_resp = login_farmer_api(from_number, password)
                if login_resp and login_resp.get("access"):
                    user_states[from_number]["access_token"] = login_resp["access"]
                    user_states[from_number]["state"] = "awaiting_crop_name"
                    send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]["welcome_back"])
                else:
                    send_whatsapp_message(from_number, "Incorrect password. Please try again.")
                    send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]["ask_loginpassword"]) # Re-ask
            else:
                # Try to register
                if register_farmer_api(user_states[from_number]["data"]):
                    login_resp = login_farmer_api(from_number, password)
                    if login_resp and login_resp.get("access"):
                        user_states[from_number]["access_token"] = login_resp["access"]
                        user_states[from_number]["state"] = "awaiting_crop_name"
                        send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]["reg_complete"])
                    else: # This case is unlikely but handled
                        send_whatsapp_message(from_number, "Login failed after registration. Please start again with 'hi'.")
                else:
                    send_whatsapp_message(from_number, "Registration failed. Please start again with 'hi'.")

        # Produce listing flow
        elif current_state == "awaiting_crop_name":
            user_states[from_number]["temp_produce"] = {"name": msg_body.title()}
            user_states[from_number]["state"] = "awaiting_state_name"
            send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]["ask_state"])

        elif current_state == "awaiting_state_name":
            state_name = msg_body.title()
            crop_name = user_states[from_number]["temp_produce"]["name"]
            
            send_whatsapp_message(from_number, f"⏳ Searching for {crop_name} prices in {state_name}...")
            price_df = get_agmarknet_prices(crop_name, state_name)
            price_summary = analyze_price_data(price_df)

            if "error" in price_summary:
                suggestion_text = "Sorry, I could not find price data for this crop. Please enter your desired price."
                send_whatsapp_message(from_number, suggestion_text)
                send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]["no_price_data"])
            else:
                suggestion_text = (
                    f"Based on {price_summary['market_count']} markets in {state_name}, the suggested price is "
                    f"₹{price_summary['min_price']} - ₹{price_summary['max_price']} per Quintal. "
                    f"The average is ₹{price_summary['avg_price']}."
                )
                send_whatsapp_message(from_number, "📈 Price Suggestion:\n" + suggestion_text)
                audio_url = generate_tts_elevenlabs(suggestion_text, lang)
                if audio_url:
                    send_whatsapp_audio(from_number, audio_url)

            # Proceed to ask for user-input price
            send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]["ask_price"])
            user_states[from_number]["state"] = "awaiting_price"

        elif current_state == "awaiting_price":
            user_states[from_number]["temp_produce"]["price_per_kg"] = msg_body
            user_states[from_number]["state"] = "awaiting_quantity"
            send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]["ask_quantity"])

        elif current_state == "awaiting_quantity":
            user_states[from_number]["temp_produce"]["quantity_kg"] = msg_body
            token = user_states[from_number].get("access_token")
            if token and add_produce_api(user_states[from_number]["temp_produce"], token):
                send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]["ask_more_crops"])
            else:
                send_whatsapp_message(from_number, "Failed to save your produce. Please try again later.")
            user_states[from_number]["state"] = "awaiting_more_crops"
            
        elif current_state == "awaiting_more_crops":
            if command in ["yes", "y", "ok", "1", "हाँ", "हां"]:
                send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]["next_crop"])
                user_states[from_number]["state"] = "awaiting_crop_name"
            else:
                send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]["thank_you"])
                user_states[from_number]["state"] = "conversation_over"

        elif current_state == "conversation_over":
            send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]["closing"])
            # Reset state for next interaction
            del user_states[from_number]["state"]


    except (IndexError, KeyError) as e:
        # Ignore non-message events from webhook
        print(f"Webhook received a non-message event or malformed data: {e}")
    except Exception as e:
        print(f"Webhook processing error: {e}")

    return "OK", 200

# ---------------------------------------------------------------------------
#                    ORDER NOTIFICATION ENDPOINT (IMPROVED)
# ---------------------------------------------------------------------------

@app.route("/notify-farmer", methods=["POST"])
def notify_farmer():
    try:
        data = request.json
        phone = data.get("phone_number")
        items = data.get("items", [])

        if not phone or not items:
            return jsonify({"error": "Invalid data: phone_number and items are required."}), 400

        user_lang = user_states.get(phone, {}).get("language", "en")

        # --- Craft separate messages for text and audio for better UX ---
        text_message_lines = []
        audio_message_parts = []

        if user_lang == 'hi':
            text_message_lines.append("🎉 *नया ऑर्डर!*")
            audio_message_parts.append("नमस्ते, आपको एक नया ऑर्डर मिला है।")
        else:
            text_message_lines.append("🎉 *New Order!*")
            audio_message_parts.append("Hello, you have a new order.")

        for item in items:
            produce_name = item.get("produce", "Unknown Produce")
            quantity_bought = item.get("quantity_bought", 0)
            remaining_stock = item.get("remaining_stock", 0)

            if user_lang == 'hi':
                text_message_lines.append(
                    f"👉 फसल: *{produce_name}*\n"
                    f"✅ बिका: *{quantity_bought}* किलो\n"
                    f"📦 बचा है: *{remaining_stock}* किलो"
                )
                audio_message_parts.append(
                    f"{quantity_bought} किलो {produce_name} बिक गया है, और अब {remaining_stock} किलो बचा है।"
                )
            else:
                text_message_lines.append(
                    f"👉 Crop: *{produce_name}*\n"
                    f"✅ Sold: *{quantity_bought}* kg\n"
                    f"📦 Left: *{remaining_stock}* kg"
                )
                audio_message_parts.append(
                    f"{quantity_bought} kilograms of {produce_name} has been sold. You have {remaining_stock} kilograms remaining."
                )

        # Send the clear, formatted text message
        text_message = "\n\n".join(text_message_lines)
        send_whatsapp_message(phone, text_message)
        
        # Generate and send the natural-sounding audio message
        combined_audio_text = " ".join(audio_message_parts)
        audio_url = generate_tts_elevenlabs(combined_audio_text, user_lang)
        if audio_url:
            send_whatsapp_audio(phone, audio_url)

        return jsonify({"status": "notification_sent"}), 200
        
    except Exception as e:
        print(f"Error in /notify-farmer endpoint: {e}")
        return jsonify({"error": str(e)}), 500

# ---------------------------------------------------------------------------
#                                MAIN
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Ensure the directory for saving audio files exists
    if not os.path.exists("static/audio"):
        os.makedirs("static/audio")
    print("WhatsApp Bot Running...")
    app.run(port=5000, debug=True)
