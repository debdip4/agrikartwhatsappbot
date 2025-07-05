import requests
from bs4 import BeautifulSoup
import logging
from datetime import datetime

AGMARKNET_URL = "https://agmarknet.gov.in/PriceAndArrivals/DatewiseCommodityReport.aspx"

def get_latest_price(commodity, state):
    """
    Scrapes Agmarknet for the latest price of a commodity in a specific state.
    This is complex due to the ASP.NET form structure.
    """
    try:
        with requests.Session() as s:
            s.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            })
            
            # 1. Initial GET to fetch viewstate and other form fields
            initial_res = s.get(AGMARKNET_URL)
            soup = BeautifulSoup(initial_res.content, 'html.parser')
            
            viewstate = soup.find(id='__VIEWSTATE').get('value')
            viewstategenerator = soup.find(id='__VIEWSTATEGENERATOR').get('value')
            eventvalidation = soup.find(id='__EVENTVALIDATION').get('value')

            today = datetime.now()
            
            # 2. Form data for the POST request
            form_data = {
                '__EVENTTARGET': '',
                '__EVENTARGUMENT': '',
                '__LASTFOCUS': '',
                '__VIEWSTATE': viewstate,
                '__VIEWSTATEGENERATOR': viewstategenerator,
                '__EVENTVALIDATION': eventvalidation,
                'ctl00$ddlLanguage': 'en',
                'ctl00$ddlState': state,
                'ctl00$ddlCommodity': commodity, # This needs exact value match
                'ctl00$txtDate': today.strftime('%d-%b-%Y'),
                'ctl00$btnSubmit': 'Submit'
            }

            # 3. POST request to get the report
            report_res = s.post(AGMARKNET_URL, data=form_data)
            report_soup = BeautifulSoup(report_res.content, 'html.parser')
            
            # 4. Find the results table and extract the price
            price_table = report_soup.find('table', {'class': 'tableagmark_new'})
            
            if not price_table:
                logging.warning(f"No price table found for {commodity} in {state}")
                return None
            
            # Find the first row with a modal price
            rows = price_table.find_all('tr')
            for row in rows[1:]: # Skip header
                cells = row.find_all('td')
                if len(cells) > 7: # Ensure row has enough columns
                    modal_price_str = cells[7].text.strip()
                    if modal_price_str.isdigit():
                        return int(modal_price_str)
            
            logging.warning(f"Modal price not found in table for {commodity} in {state}")
            return None

    except Exception as e:
        logging.error(f"Error scraping Agmarknet: {e}")
        return None

# Example usage (for testing):
# if __name__ == '__main__':
#     price = get_latest_price('Potato', 'Uttar Pradesh')
#     if price:
#         print(f"Latest modal price for Potato in Uttar Pradesh is: {price} per Quintal")
#     else:
#         print("Could not retrieve price.")
