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

# --- In-memory database for hackathon prototype ---
user_states = {}

# --- Dictionary to hold all your public audio file URLs ---
AUDIO_CLIPS = {
    "welcome": "https://raw.github.com/debdip4/agrikartwhatsappbot/main/Audio_files/welcome.mp3",
    "en": {
        "ask_name": "https://raw.github.com/debdip4/agrikartwhatsappbot/main/Audio_files/en_ask_name.mp3",
        "ask_address": "https://raw.github.com/debdip4/agrikartwhatsappbot/main/Audio_files/en_ask_address.mp3",
        "ask_pincode": "https://raw.github.com/debdip4/agrikartwhatsappbot/main/Audio_files/en_ask_pincode.mp3",
        "ask_password": "https://raw.github.com/debdip4/agrikartwhatsappbot/main/Audio_files/en_ask_password.mp3",
        "reg_complete": "https://raw.github.com/debdip4/agrikartwhatsappbot/main/Audio_files/en_reg_complete.mp3",
        "ask_price": "https://raw.github.com/debdip4/agrikartwhatsappbot/main/Audio_files/en_ask_price.mp3",
        "ask_quantity": "https://raw.github.com/debdip4/agrikartwhatsappbot/main/Audio_files/en_ask_quantity.mp3",
        "ask_more_crops": "https://raw.github.com/debdip4/agrikartwhatsappbot/main/Audio_files/en_ask_more_crops.mp3",
        "next_crop": "https://raw.github.com/debdip4/agrikartwhatsappbot/main/Audio_files/en_next_crop.mp3",
        "thank_you": "https://raw.github.com/debdip4/agrikartwhatsappbot/main/Audio_files/en_thank_you.mp3",
        "welcome_back": "https://raw.github.com/debdip4/agrikartwhatsappbot/main/Audio_files/en_welcome_back.mp3",
        "closing": "https://raw.github.com/debdip4/agrikartwhatsappbot/main/Audio_files/en_closing.mp3",
        "ask_loginpassword": "https://raw.github.com/debdip4/agrikartwhatsappbot/main/Audio_files/en_ask_loginpassword.mp3",
        "ask_state": "https://raw.github.com/debdip4/agrikartwhatsappbot/main/Audio_files/en_ask_state.mp3",
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
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    except Exception as e:
        print(f"WebDriver initialisation failed: {e}")
        return None

    try:
        url = "https://agmarknet.gov.in/SearchCmmMkt.aspx"
        driver.get(url)
        driver.set_page_load_timeout(30)

        Select(driver.find_element(By.ID, "ddlCommodity")).select_by_visible_text(commodity_name)
        Select(driver.find_element(By.ID, "ddlState")).select_by_visible_text(state_name)
        driver.find_element(By.ID, "btnGo").click()

        wait = WebDriverWait(driver, 25)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#cphBody_GridPriceData tbody tr")))

        table_html = driver.find_element(By.ID, "cphBody_GridPriceData").get_attribute("outerHTML")
        df_list = pd.read_html(StringIO(table_html))
        if not df_list:
            return None
        df = df_list[0]
        if "No Data Found" in df.to_string():
            return None
        return df
    except Exception as e:
        print(f"Scraping error: {e}")
        return None
    finally:
        if driver:
            driver.quit()


def analyze_price_data(price_df: pd.DataFrame):
    """Returns basic statistics for price suggestion."""

    price_col = "Modal Price (Rs./Quintal)"
    modal_prices = pd.to_numeric(price_df[price_col], errors="coerce").dropna()
    if modal_prices.empty:
        return {"error": "No valid prices found."}

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
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    payload = {"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": msg}}
    requests.post(url, headers=headers, json=payload)


def send_whatsapp_audio(to: str, url_link: str):
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    payload = {"messaging_product": "whatsapp", "to": to, "type": "audio", "audio": {"link": url_link}}
    requests.post(url, headers=headers, json=payload)

# ---------------------------------------------------------------------------
#                  EXISTING BACKEND API HELPERS (UNCHANGED)
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
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
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

# ---------------------------------------------------------------------------
#                       TEXT TO SPEECH WITH ELEVENLABS
# ---------------------------------------------------------------------------

def generate_tts_elevenlabs(text, lang="en", voice="Bella"):
    try:
        eleven_api_key = os.getenv("ELEVENLABS_API_KEY")
        voice_id = "EXAVITQu4vr4xnSDxMaL"
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?optimize_streaming_latency=0"
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": eleven_api_key,
        }

        response = requests.post(
            url,
            headers=headers,
            json={
                "text": text,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
            },
            timeout=30,
        )

        if response.status_code == 200:
            filename = f"{int(time.time())}_{voice}.mp3"
            path = os.path.join("static/audio", filename)
            with open(path, "wb") as f:
                f.write(response.content)
            public_url = os.getenv("PUBLIC_AUDIO_BASE_URL", "")
            return f"{public_url}/static/audio/{filename}"
        else:
            print(f"ElevenLabs error {response.status_code}: {response.text}")
            return None
    except Exception as e:
        print(f"TTS generation error: {e}")
        return None

# ---------------------------------------------------------------------------
#                                   WEBHOOK
# ---------------------------------------------------------------------------

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.verify_token") == VERIFY_TOKEN:
            return request.args.get("hub.challenge"), 200
        return "Unauthorized", 403

    data = request.get_json()
    try:
        entry = data.get("entry", [])[0]
        change = entry.get("changes", [])[0]
        value = change.get("value", {})
        messages = value.get("messages")

        if not messages:
            return "OK", 200

        message = messages[0]
        from_number = message["from"]
        msg_body = message["text"]["body"].strip()
        command = msg_body.lower()

        # Initialise state storage for new user
        if from_number not in user_states:
            user_states[from_number] = {"data": {}}

        current_state = user_states[from_number].get("state")

        # Greeting to start flow
        if command in ["hi", "hello", "नमस्ते"]:
            if check_farmer_exists(from_number):
                user_states[from_number]["state"] = "awaiting_lang_after_exists"
            else:
                user_states[from_number]["state"] = "awaiting_language_choice"
            send_whatsapp_audio(from_number, AUDIO_CLIPS["welcome"])
            return "OK", 200

        # ---------------- STATE MACHINE ----------------
        if current_state == "awaiting_lang_after_exists":
            lang = "en" if "1" in command else "hi"
            user_states[from_number]["language"] = lang
            last_password = user_states[from_number]["data"].get("password")
            if last_password:
                login_resp = login_farmer_api(from_number, last_password)
                if login_resp and login_resp.get("access"):
                    user_states[from_number]["access_token"] = login_resp["access"]
                    user_states[from_number]["state"] = "awaiting_crop_name"
                    send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]["welcome_back"])
                else:
                    send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]["ask_password"])
                    user_states[from_number]["state"] = "awaiting_password"
            else:
                send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]["ask_loginpassword"])
                user_states[from_number]["state"] = "awaiting_password"

        elif current_state == "awaiting_language_choice":
            lang = "en" if "1" in command else "hi"
            user_states[from_number]["language"] = lang
            user_states[from_number]["state"] = "awaiting_name"
            send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]["ask_name"])

        elif current_state == "awaiting_name":
            lang = user_states[from_number]["language"]
            user_states[from_number]["data"]["name"] = msg_body
            user_states[from_number]["state"] = "awaiting_address"
            send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]["ask_address"])

        elif current_state == "awaiting_address":
            lang = user_states[from_number]["language"]
            user_states[from_number]["data"]["address"] = msg_body
            user_states[from_number]["state"] = "awaiting_password"
            send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]["ask_password"])

        elif current_state == "awaiting_password":
            lang = user_states[from_number]["language"]
            user_states[from_number]["data"]["password"] = msg_body
            user_states[from_number]["data"]["username"] = from_number
            user_states[from_number]["data"]["phone_number"] = from_number

            if check_farmer_exists(from_number):
                login_resp = login_farmer_api(from_number, msg_body)
                if login_resp and login_resp.get("access"):
                    user_states[from_number]["access_token"] = login_resp["access"]
                    user_states[from_number]["state"] = "awaiting_crop_name"
                    send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]["welcome_back"])
                else:
                    send_whatsapp_message(from_number, "Incorrect password. Please try again.")
            else:
                if register_farmer_api(user_states[from_number]["data"]):
                    login_resp = login_farmer_api(from_number, msg_body)
                    if login_resp and login_resp.get("access"):
                        user_states[from_number]["access_token"] = login_resp["access"]
                        user_states[from_number]["state"] = "awaiting_crop_name"
                        send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]["reg_complete"])
                    else:
                        send_whatsapp_message(from_number, "Registration failed. Please start again with 'hi'.")

        elif current_state == "awaiting_crop_name":
            lang = user_states[from_number]["language"]
            crop_name = msg_body
            user_states[from_number]["temp_produce"] = {"name": crop_name}
            user_states[from_number]["state"] = "awaiting_state_name"
            send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]["ask_state"])

        elif current_state == "awaiting_state_name":
            lang = user_states[from_number]["language"]
            state_name = msg_body
            temp = user_states[from_number]["temp_produce"]
            temp["state"] = state_name

            # Fetch and analyse prices
            price_df = get_agmarknet_prices(temp["name"], state_name)
            if price_df is not None:
                price_summary = analyze_price_data(price_df)
                if "error" not in price_summary:
                    suggestion_text = (
                        "Based on "
                        + str(price_summary["market_count"])
                        + f" market reports in {state_name}, recommended price range is Rs {price_summary['min_price']:.2f} - Rs {price_summary['max_price']:.2f} per quintal. "
                        + f"Average price is Rs {price_summary['avg_price']:.2f}."
                    )
                else:
                    suggestion_text = price_summary["error"]
            else:
                suggestion_text = "Could not retrieve price data at the moment."

            send_whatsapp_message(from_number, suggestion_text)
            audio_url = generate_tts_elevenlabs(suggestion_text, lang)
            if audio_url:
                send_whatsapp_audio(from_number, audio_url)

            # Proceed to ask user-entered price
            send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]["ask_price"])
            user_states[from_number]["state"] = "awaiting_price"

        elif current_state == "awaiting_price":
            lang = user_states[from_number]["language"]
            user_states[from_number]["temp_produce"]["price_per_kg"] = msg_body
            user_states[from_number]["state"] = "awaiting_quantity"
            send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]["ask_quantity"])

        elif current_state == "awaiting_quantity":
            lang = user_states[from_number]["language"]
            user_states[from_number]["temp_produce"]["quantity_kg"] = msg_body
            token = user_states[from_number].get("access_token")
            if token and add_produce_api(user_states[from_number]["temp_produce"], token):
                send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]["ask_more_crops"])
            else:
                send_whatsapp_message(from_number, "Failed to save produce. Try again later.")
            user_states[from_number]["state"] = "awaiting_more_crops"

        elif current_state == "awaiting_more_crops":
            lang = user_states[from_number]["language"]
            if command in ["yes", "y", "ok", "हाँ", "हां"]:
                send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]["next_crop"])
                user_states[from_number]["state"] = "awaiting_crop_name"
            else:
                send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]["thank_you"])
                user_states[from_number]["state"] = "conversation_over"

        elif current_state == "conversation_over":
            lang = user_states[from_number]["language"]
            send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]["closing"])

    except Exception as e:
        print(f"Webhook processing error: {e}")

    return "OK", 200

# ---------------------------------------------------------------------------
#                    ORDER NOTIFICATION ENDPOINT (UPDATED)
# ---------------------------------------------------------------------------

@app.route("/notify-farmer", methods=["POST"])
def notify_farmer():
    try:
        data = request.json
        phone = data.get("phone_number")
        items = data.get("items", [])

        if not phone or not items:
            return jsonify({"error": "Invalid data"}), 400

        user_lang = user_states.get(phone, {}).get("language", "en")

        lines = []
        if user_lang == "hi":
            lines.append("नया ऑर्डर")
        else:
            lines.append("New order")

        for item in items:
            produce_name = item["produce"]
            quantity_bought = item["quantity_bought"]
            remaining_stock = item["remaining_stock"]

            if user_lang == "hi":
                lines.append(
                    f"फसल: {produce_name}\nबिक गया: {quantity_bought} किलो\nबचा है: {remaining_stock} किलो"
                )
            else:
                lines.append(
                    f"Crop: {produce_name}\nSold: {quantity_bought} kg\nLeft: {remaining_stock} kg"
                )

        message = "\n\n".join(lines)
        send_whatsapp_message(phone, message)

        combined_audio_text = " ".join(lines)
        audio_url = generate_tts_elevenlabs(combined_audio_text, user_lang)
        if audio_url:
            send_whatsapp_audio(phone, audio_url)

        return jsonify({"status": "sent"}), 200
    except Exception as e:
        print(f"Notify farmer error: {e}")
        return jsonify({"error": str(e)}), 500

# ---------------------------------------------------------------------------
#                                MAIN
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("WhatsApp Bot Running...")
    if not os.path.exists("static/audio"):
        os.makedirs("static/audio")
    app.run(port=5000, debug=True)
