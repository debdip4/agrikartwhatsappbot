import requests
import json
import logging
from config import ACCESS_TOKEN, WHATSAPP_API_URL

def send_whatsapp_message(to, message_type, data):
    """Generic function to send a message via WhatsApp API."""
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": message_type,
        message_type: data,
    }
    try:
        response = requests.post(WHATSAPP_API_URL, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        logging.info(f"Message sent to {to}. Response: {response.json()}")
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to send message to {to}: {e}")
        logging.error(f"Response body: {e.response.text if e.response else 'No response'}")
        return None

def send_text_message(to, text):
    """Sends a simple text message."""
    data = {"preview_url": False, "body": text}
    return send_whatsapp_message(to, "text", data)

def send_audio_message(to, audio_url):
    """Sends an audio message from a URL."""
    data = {"link": audio_url}
    return send_whatsapp_message(to, "audio", data)
