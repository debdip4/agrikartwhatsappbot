"""Agrikart WhatsApp Bot (integrated Agmarknet price suggestion)
-------------------------------------------------------------
State‑level price data only (no all‑India fallback).
No emojis in code.
"""

import os
import json
import time
import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# Price‑scraping dependencies
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

# ---------------------------------------------------------------------------
# Credentials / Config
# ---------------------------------------------------------------------------
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
API_BASE_URL = os.getenv("BACKEND_API_BASE_URL")
PUBLIC_AUDIO_BASE_URL = os.getenv("PUBLIC_AUDIO_BASE_URL", "")  # e.g. Ngrok URL

# ---------------------------------------------------------------------------
# In‑memory state store (fine for prototype)
# ---------------------------------------------------------------------------
user_states: dict = {}

# ---------------------------------------------------------------------------
# Audio clip URLs
# ---------------------------------------------------------------------------
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
    },
}

# ---------------------------------------------------------------------------
# Agmarknet scraper
# ---------------------------------------------------------------------------

def get_agmarknet_prices(commodity_name: str, state_name: str):
    """Return DataFrame of price data or None; strictly state‑level."""
    print(f"Scraping {commodity_name} in state {state_name}…")
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = None
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.get("https://agmarknet.gov.in/SearchCmmMkt.aspx")
        driver.set_page_load_timeout(30)

        Select(driver.find_element(By.ID, "ddlCommodity")).select_by_visible_text(commodity_name)
        Select(driver.find_element(By.ID, "ddlState")).select_by_visible_text(state_name)
        driver.find_element(By.ID, "btnGo").click()

        WebDriverWait(driver, 25).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#cphBody_GridPriceData tbody tr"))
        )

        table_html = driver.find_element(By.ID, "cphBody_GridPriceData").get_attribute("outerHTML")
        df_list = pd.read_html(StringIO(table_html))
        if not df_list:
            print("No tables parsed.")
            return None
        df = df_list[0]
        if "No Data Found" in df.to_string():
            print("Table reports 'No Data Found'.")
            return None

        if len(df.columns) == 12:
            df.columns = [
                "Sl No.",
                "State",
                "District",
                "Market",
                "Group",
                "Commodity",
                "Variety",
                "Grade",
                "Min Price",
                "Max Price",
                "Modal Price (Rs./Quintal)",
                "Date",
            ]
        print("Scrape successful.")
        return df
    except Exception as exc:
        print(f"Scraper error: {exc}")
        return None
    finally:
        if driver:
            driver.quit()


def analyze_price_data(df: pd.DataFrame):
    col = "Modal Price (Rs./Quintal)"
    if col not in df.columns:
        return {"error": "Modal price column missing."}
    prices = pd.to_numeric(df[col], errors="coerce").dropna()
    if prices.empty:
        return {"error": "No valid price data."}
    return {
        "market_count": len(prices),
        "min_price": prices.min(),
        "max_price": prices.max(),
        "avg_price": round(prices.mean(), 2),
    }

# ---------------------------------------------------------------------------
# WhatsApp helpers
# ---------------------------------------------------------------------------

def _wa_post(payload: dict):
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=20)
    if resp.status_code >= 300:
        print(f"WhatsApp API error {resp.status_code}: {resp.text}")
    return resp


def send_whatsapp_message(to: str, body: str):
    _wa_post({
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": body},
    })


def send_whatsapp_audio(to: str, link: str):
    _wa_post({
        "messaging_product": "whatsapp",
        "to": to,
        "type": "audio",
        "audio": {"link": link},
    })

# ---------------------------------------------------------------------------
# Backend API helpers
# ---------------------------------------------------------------------------

def check_farmer_exists(phone_number: str):
    try:
        resp = requests.get(f"{API_BASE_URL}/api/v1/farmer/check/{phone_number}/", timeout=15)
        return resp.status_code == 200 and resp.json().get("exists", False)
    except requests.RequestException as exc:
        print(f"Farmer exists check error: {exc}")
        return False


def register_farmer_api(user: dict):
    try:
        resp = requests.post(f"{API_BASE_URL}/api
