import os
import logging
from flask import Flask, request, jsonify

from config import VERIFY_TOKEN, AUDIO_CLIPS, CATEGORIES_EN, PRODUCTS_EN, CATEGORIES_HI
from state_manager import StateManager
from whatsapp_helpers import send_text_message, send_audio_message
import backend_api_client as api
import agmarknet_scraper

# --- Flask App Initialization ---
app = Flask(__name__)

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Main Webhook Logic ---
@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        # Meta Webhook Verification
        if request.args.get("hub.verify_token") == VERIFY_TOKEN:
            return request.args.get("hub.challenge"), 200
        return "Invalid verification token", 403

    if request.method == "POST":
        data = request.get_json()
        logging.info(f"Received data: {data}")

        # Ensure it's a WhatsApp message update
        if "entry" in data and "changes" in data["entry"][0]:
            change = data["entry"][0]["changes"][0]
            if "messages" in change["value"]:
                message_data = change["value"]["messages"][0]
                from_number = message_data["from"]
                msg_body = message_data.get("text", {}).get("body", "").strip().lower()

                # Get user's current state
                user_state = StateManager.get_user_state(from_number)
                
                # Process the message based on state
                process_message(from_number, msg_body, user_state)

        return jsonify({"status": "ok"}), 200

def process_message(phone, msg, state):
    """Main logic tree for processing user messages."""
    stage = state.get('stage')
    lang = state.get('language', 'en') # Default to English

    # --- Initial Contact or Reset ---
    if not stage:
        if api.check_farmer_exists(phone):
            # Existing User
            state['stage'] = 'awaiting_login_password'
            lang = state.get('language', 'en') # Retrieve stored language if available
            send_audio_message(phone, AUDIO_CLIPS[lang]['welcome_back'])
            send_audio_message(phone, AUDIO_CLIPS[lang]['ask_loginpassword'])
        else:
            # New User
            state['stage'] = 'awaiting_language_selection'
            state['registration_details'] = {'phone': phone}
            send_audio_message(phone, AUDIO_CLIPS['welcome'])
            send_text_message(phone, "Please select your language:\n1. English\n2. हिंदी (Hindi)")
        StateManager.set_user_state(phone, state)
        return

    # --- Language Selection ---
    if stage == 'awaiting_language_selection':
        if '1' in msg:
            state['language'] = 'en'
            send_audio_message(phone, AUDIO_CLIPS['en']['ask_name'])
            state['stage'] = 'awaiting_name'
        elif '2' in msg:
            state['language'] = 'hi'
            send_audio_message(phone, AUDIO_CLIPS['hi']['ask_name'])
            state['stage'] = 'awaiting_name'
        else:
            send_text_message(phone, "Invalid selection. Please press 1 for English or 2 for Hindi.")
        StateManager.set_user_state(phone, state)
        return

    # --- Registration Flow ---
    if stage == 'awaiting_name':
        state['registration_details']['name'] = msg.title()
        state['stage'] = 'awaiting_address'
        send_audio_message(phone, AUDIO_CLIPS[lang]['ask_address'])
    elif stage == 'awaiting_address':
        state['registration_details']['address'] = msg
        state['stage'] = 'awaiting_state'
        send_audio_message(phone, AUDIO_CLIPS[lang]['ask_state'])
    elif stage == 'awaiting_state':
        state['registration_details']['state'] = msg.title()
        state['stage'] = 'awaiting_pincode'
        send_audio_message(phone, AUDIO_CLIPS[lang]['ask_pincode'])
    elif stage == 'awaiting_pincode':
        if msg.isdigit() and len(msg) == 6:
            state['registration_details']['pincode'] = msg
            state['stage'] = 'awaiting_password'
            send_audio_message(phone, AUDIO_CLIPS[lang]['ask_password'])
        else:
            send_text_message(phone, "Invalid Pincode. Please enter a 6-digit number.")
    elif stage == 'awaiting_password':
        state['registration_details']['password'] = msg
        # Register the farmer
        if api.register_farmer(state['registration_details']):
            # Login to get token
            token = api.login_farmer(phone, msg)
            if token:
                state['token'] = token
                state['stage'] = 'awaiting_category'
                send_audio_message(phone, AUDIO_CLIPS[lang]['reg_complete'])
                prompt_for_category(phone, lang)
            else:
                send_text_message(phone, "Registration successful, but login failed. Please try logging in again later.")
                StateManager.reset_user_state(phone)
        else:
            send_text_message(phone, "Registration failed. Please try again.")
            StateManager.reset_user_state(phone)

    # --- Login Flow ---
    elif stage == 'awaiting_login_password':
        token = api.login_farmer(phone, msg)
        if token:
            state['token'] = token
            state['stage'] = 'awaiting_category'
            send_audio_message(phone, AUDIO_CLIPS[lang]['next_crop'])
            prompt_for_category(phone, lang)
        else:
            send_text_message(phone, "Login failed. Incorrect password. Please try again.")
            send_audio_message(phone, AUDIO_CLIPS[lang]['ask_loginpassword'])

    # --- Produce Listing Flow ---
    elif stage == 'awaiting_category':
        categories = CATEGORIES_EN if lang == 'en' else CATEGORIES_HI
        if msg in categories:
            category_name = CATEGORIES_EN[msg] # Use English name for backend
            state['current_produce'] = {'category': category_name}
            state['stage'] = 'awaiting_product_selection'
            prompt_for_product(phone, lang, category_name)
        else:
            send_text_message(phone, "Invalid selection. Please choose a valid category number.")
    
    elif stage == 'awaiting_product_selection':
        try:
            selection_index = int(msg) - 1
            category = state['current_produce']['category']
            product_list = PRODUCTS_EN[category]
            if 0 <= selection_index < len(product_list):
                product_name = product_list[selection_index]
                state['current_produce']['name'] = product_name
                
                # Scrape price and suggest
                farmer_state = state.get('registration_details', {}).get('state', '') # Need farmer's state
                if farmer_state:
                    price = agmarknet_scraper.get_latest_price(product_name, farmer_state)
                    if price:
                        price_per_kg = round(price / 100, 2)
                        suggestion = f"The current market rate for {product_name} in {farmer_state} is around ₹{price_per_kg}/Kg. You can set your own price."
                        if lang == 'hi':
                           suggestion = f"{farmer_state} में {product_name} का मौजूदा बाजार भाव लगभग ₹{price_per_kg}/किलो है। आप अपनी कीमत खुद तय कर सकते हैं।"
                        send_text_message(phone, suggestion)

                state['stage'] = 'awaiting_price'
                send_audio_message(phone, AUDIO_CLIPS[lang]['ask_price'])
            else:
                send_text_message(phone, "Invalid selection.")
        except ValueError:
            send_text_message(phone, "Please enter a valid number.")

    elif stage == 'awaiting_price':
        try:
            price = float(msg)
            state['current_produce']['price_per_kg'] = price
            state['stage'] = 'awaiting_quantity'
            send_audio_message(phone, AUDIO_CLIPS[lang]['ask_quantity'])
        except ValueError:
            send_text_message(phone, "Please enter a valid price (e.g., 50 or 55.5).")

    elif stage == 'awaiting_quantity':
        try:
            quantity = float(msg)
            state['current_produce']['quantity_kg'] = quantity
            # Add produce to backend
            if api.add_produce(state['token'], state['current_produce']):
                msg_text = f"{state['current_produce']['name']} has been listed successfully!"
                if lang == 'hi':
                    msg_text = f"{state['current_produce']['name']} सफलतापूर्वक सूचीबद्ध हो गया है!"
                send_text_message(phone, msg_text)
                state['stage'] = 'awaiting_more_crops'
                send_audio_message(phone, AUDIO_CLIPS[lang]['ask_more_crops'])
                send_text_message(phone, "1. Yes\n2. No")
            else:
                send_text_message(phone, "Could not list your produce. Please try again later.")
                StateManager.reset_user_state(phone)
        except ValueError:
             send_text_message(phone, "Please enter a valid quantity in Kg (e.g., 100 or 50.5).")

    elif stage == 'awaiting_more_crops':
        if msg == '1' or msg == 'yes':
            state['stage'] = 'awaiting_category'
            send_audio_message(phone, AUDIO_CLIPS[lang]['next_crop'])
            prompt_for_category(phone, lang)
        elif msg == '2' or msg == 'no':
            StateManager.reset_user_state(phone)
            state['stage'] = 'finished'
            send_audio_message(phone, AUDIO_CLIPS[lang]['thank_you'])
        else:
            send_text_message(phone, "Invalid input. Please enter 1 for Yes or 2 for No.")
            
    # --- Closing ---
    if 'thank you' in msg or 'dhanyawad' in msg:
        send_audio_message(phone, AUDIO_CLIPS[lang]['closing'])
        StateManager.reset_user_state(phone) # Reset state for next interaction
        state['stage'] = None
            
    # Save the updated state
    StateManager.set_user_state(phone, state)


def prompt_for_category(phone, lang):
    """Sends the category list to the user."""
    if lang == 'en':
        categories = CATEGORIES_EN
        header = "Please select a category for your produce:"
    else:
        categories = CATEGORIES_HI
        header = "कृपया अपनी उपज के लिए एक श्रेणी चुनें:"
    
    category_list = "\n".join([f"{num}. {name}" for num, name in categories.items()])
    send_text_message(phone, f"{header}\n{category_list}")

def prompt_for_product(phone, lang, category_name):
    """Sends the product list for the chosen category."""
    product_list = PRODUCTS_EN.get(category_name, [])
    if not product_list:
        send_text_message(phone, "No products found for this category.")
        return
        
    header = f"Select a product from {category_name}:"
    if lang == 'hi':
        header = f"{category_name} से एक उत्पाद चुनें:"
        
    product_text = "\n".join([f"{i+1}. {product}" for i, product in enumerate(product_list)])
    send_text_message(phone, f"{header}\n{product_text}")


# --- Notification Endpoint ---
@app.route("/notify", methods=["POST"])
def notify_farmer():
    """Endpoint for the backend to call when a product is sold."""
    data = request.get_json()
    if not data or "phone" not in data or "message" not in data:
        return jsonify({"error": "Invalid payload. 'phone' and 'message' are required."}), 400
    
    phone_number = data["phone"]
    message = data["message"]
    
    send_text_message(phone_number, f"🎉 *Purchase Notification* 🎉\n\n{message}")
    
    return jsonify({"status": "notification_sent"}), 200


# --- Run the App ---
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), debug=True)
