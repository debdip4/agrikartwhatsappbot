import os
import json
import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import time

# --- NEWLY ADDED IMPORTS for Price Bot ---
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
# -----------------------------------------

load_dotenv()
app = Flask(__name__)

# --- Load Credentials ---
ACCESS_TOKEN = os.getenv('ACCESS_TOKEN')
VERIFY_TOKEN = os.getenv('VERIFY_TOKEN')
PHONE_NUMBER_ID = os.getenv('PHONE_NUMBER_ID')
API_BASE_URL = os.getenv('BACKEND_API_BASE_URL')

# In-memory database for hackathon prototype
user_states = {}

# Your AUDIO_CLIPS dictionary remains here...
AUDIO_CLIPS = {
    # ... your audio clips ...
}

# --- Price Bot Functions (get_agmarknet_prices, analyze_price_data) remain here ---
def get_agmarknet_prices(commodity_name: str, state_name: str):
    # ... full function code ...
    pass
def analyze_price_data(price_df: pd.DataFrame):
    # ... full function code ...
    pass

# --- API & Messaging Helpers remain here ---
def check_farmer_exists(phone_number):
    # ... full function code ...
    pass
def register_farmer_api(user_data):
    # ... full function code ...
    pass
def login_farmer_api(username, password):
    # ... full function code ...
    pass
def add_produce_api(produce_data, access_token):
    # ... full function code ...
    pass
def send_whatsapp_message(to, msg):
    # ... full function code ...
    pass
def send_whatsapp_audio(to, url_link):
    # ... full function code ...
    pass

# --- TTS Function ---
def generate_tts_elevenlabs(text, lang='en'):
    try:
        eleven_api_key = os.getenv('ELEVENLABS_API_KEY')
        VOICE_ID = "EXAVITQu4vr4xnSDxMaL"  # Example Voice ID

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": eleven_api_key
        }

        response = requests.post(url, headers=headers, json={
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}
        })

        if response.status_code == 200:
            filename = f"{int(time.time())}.mp3"
            # Ensure the directory exists
            os.makedirs('static/audio', exist_ok=True)
            path = os.path.join("static/audio", filename)
            with open(path, 'wb') as f:
                f.write(response.content)
            
            # IMPORTANT: Replace with your actual public URL from deployment
            # For local testing, you might use ngrok.
            base_url = os.getenv('PUBLIC_URL', '') 
            return f"{base_url}/static/audio/{filename}"
        else:
            print(f"❌ ElevenLabs error: {response.status_code}, {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error generating audio via ElevenLabs: {e}")
        return None

# --- Webhook ---
@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        # ... (webhook verification) ...
        pass

    data = request.get_json()
    try:
        message = data["entry"][0]["changes"][0]["value"]["messages"][0]
        from_number = message['from']
        msg_body = message['text']['body']
        command = msg_body.strip().lower()

        if from_number not in user_states:
            user_states[from_number] = {"data": {}}
        current_state = user_states[from_number].get("state")
        
        # --- MODIFIED REGISTRATION FLOW ---

        # ... (awaiting_language_choice and awaiting_name states are unchanged) ...

        elif current_state == 'awaiting_address':
            lang = user_states[from_number]['language']
            user_states[from_number]['data']['address'] = msg_body
            
            # --- NEW: Ask for state ---
            user_states[from_number]['state'] = 'awaiting_state'
            ask_state_text = "What state are you in?" if lang == 'en' else "आप किस राज्य में हैं?"
            audio_url = generate_tts_elevenlabs(ask_state_text, lang)
            if audio_url:
                send_whatsapp_audio(from_number, audio_url)
            else:
                send_whatsapp_message(from_number, ask_state_text)

        # --- NEW STATE to handle the response ---
        elif current_state == 'awaiting_state':
            lang = user_states[from_number]['language']
            # Save the state name, capitalizing it for consistency
            user_states[from_number]['data']['state'] = msg_body.strip().title()
            
            # Now, proceed to ask for the password
            user_states[from_number]['state'] = 'awaiting_password'
            send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]['ask_password'])

        # ... (awaiting_password logic is unchanged) ...


        # --- MODIFIED CROP LISTING FLOW ---
        elif current_state == 'awaiting_crop_name':
            lang = user_states[from_number]['language']
            crop_name = msg_body.strip().title()
            user_states[from_number]['temp_produce'] = {'name': crop_name}

            # --- DYNAMICALLY USE THE SAVED STATE ---
            state_name = user_states[from_number].get('data', {}).get('state')

            if not state_name:
                send_whatsapp_message(from_number, "I don't have your state on file. Please start over by saying 'hi'.")
                return 'OK', 200

            price_df = get_agmarknet_prices(crop_name, state_name)
            
            if price_df is not None:
                price_summary = analyze_price_data(price_df)
                if price_summary:
                    min_p = price_summary['min_price']
                    max_p = price_summary['max_price']
                    avg_p = price_summary['avg_price']

                    if lang == 'hi':
                        suggestion_text = (
                            f"🤖 सुझाव:\n{state_name} में {crop_name} का भाव ₹{min_p:.0f} से ₹{max_p:.0f} प्रति क्विंटल के बीच है। "
                            f"औसत भाव ₹{avg_p:.0f} है।"
                        )
                    else:
                        suggestion_text = (
                            f"🤖 Suggestion:\nPrices for {crop_name} in {state_name} range from ₹{min_p:.0f} to ₹{max_p:.0f} per quintal. "
                            f"The average price is ₹{avg_p:.0f}."
                        )
                    send_whatsapp_message(from_number, suggestion_text)
                else:
                    send_whatsapp_message(from_number, "📉 Not enough data to suggest a price.")
            else:
                send_whatsapp_message(from_number, f"📉 Sorry, could not find any recent price data for {crop_name} in {state_name}.")

            send_whatsapp_audio(from_number, AUDIO_CLIPS[lang]['ask_price'])
            user_states[from_number]['state'] = 'awaiting_price'

        # ... (Other states remain unchanged) ...

    except Exception as e:
        print(f"❌ Error in webhook: {e}")
    return 'OK', 200

# ... (notify_farmer and __main__ block remain unchanged) ...
