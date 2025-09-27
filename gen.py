import os
import random
import time
import asyncio
import threading
import csv
import pycountry
import re
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# Bot configuration
API_ID = 28075471
API_HASH = "6db86d600105807f18519ebbb515d676"
BOT_TOKEN = "7581455235:AAGVF7FZVuLmIYxszbAtdJzjB_N_iJjjL5s"

# Initialize the Pyrogram Client
app = Client("cc_gen_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Load BIN data from CSV
bin_data = {}
csv_file_path = "bins_all.csv"

def load_bin_data():
    """Load BIN data from CSV file"""
    global bin_data
    if not os.path.exists(csv_file_path):
        print(f"Warning: {csv_file_path} not found. BIN lookup will not work.")
        return
    
    with open(csv_file_path, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            bin_number = row['number']
            bin_data[bin_number] = {
                'country_code': row['country'],
                'flag': row['flag'],
                'vendor': row['vendor'],
                'type': row['type'],
                'level': row['level'],
                'bank_name': row['bank_name']
            }
    print(f"Loaded {len(bin_data)} BIN records from {csv_file_path}")

def get_country_name(country_code):
    """Convert country code to full country name"""
    try:
        country = pycountry.countries.get(alpha_2=country_code)
        return country.name if country else country_code
    except:
        return country_code

def is_valid_bin(bin_code):
    """Check if BIN exists in our database"""
    # Check exact match
    if bin_code in bin_data:
        return True
    
    # Check partial matches (shorter BINs)
    for length in range(len(bin_code)-1, 4, -1):
        partial_bin = bin_code[:length]
        if partial_bin in bin_data:
            return True
    
    return False

# Luhn algorithm checker
async def checkLuhn(cardNo):
    nDigits = len(cardNo)
    nSum = 0
    isSecond = False
    for i in range(nDigits - 1, -1, -1):
        d = ord(cardNo[i]) - ord("0")
        if isSecond == True:
            d = d * 2
        nSum += d // 10
        nSum += d % 10
        isSecond = not isSecond
    return nSum % 10 == 0

def clean_bin_input(bin_input):
    """Clean and extract just the BIN part from various inputs"""
    # Remove any non-digit characters first
    clean_bin = re.sub(r'\D', '', bin_input)
    return clean_bin

# Card generator function - FIXED to preserve given digits
async def cc_genarator(cc, mes, ano, cvv):
    cc, mes, ano, cvv = str(cc), str(mes), str(ano), str(cvv)
    
    # Clean the BIN input but preserve all given digits
    clean_cc = clean_bin_input(cc)
    
    # Handle month - ensure proper format
    if mes == "None" or 'X' in mes or 'x' in mes or 'rnd' in mes or not mes.isdigit():
        mes = str(random.randint(1, 12))
        if len(mes) == 1:
            mes = "0" + mes
    elif mes != "None" and len(mes) == 1:
        mes = "0" + mes
    elif len(mes) > 2:
        mes = mes[:2]  # Take only first 2 digits

    # Handle year - ensure proper format
    if ano == "None" or 'X' in ano or 'x' in ano or 'rnd' in ano or not ano.isdigit():
        ano = str(random.randint(2024, 2035))
    elif ano != "None" and len(ano) == 2:
        ano = "20" + ano
    elif len(ano) > 4:
        ano = ano[:4]  # Take only first 4 digits

    # Determine card type and length based on given BIN
    is_amex = clean_cc.startswith(('34', '37'))
    
    if is_amex:
        card_length = 15  # Amex has 15 digits
        cvv_length = 4    # Amex has 4-digit CVV
    else:
        card_length = 16  # Most cards have 16 digits
        cvv_length = 3    # Most cards have 3-digit CVV

    # Generate only the remaining digits needed
    numbers = list("0123456789")
    random.shuffle(numbers)
    random_digits = "".join(numbers)
    
    # Calculate how many digits we need to generate to complete the card
    digits_needed = card_length - len(clean_cc)
    if digits_needed > 0:
        cc_result = clean_cc + random_digits[:digits_needed]
    else:
        # If given digits are already longer than needed, truncate
        cc_result = clean_cc[:card_length]

    # Handle CVV - ensure proper format
    if cvv == "None" or 'x' in cvv or 'X' in cvv or 'rnd' in cvv or not cvv.isdigit():
        if is_amex:
            cvv_result = str(random.randint(1000, 9999))  # Amex has 4-digit CVV
        else:
            cvv_result = str(random.randint(100, 999))    # Others have 3-digit CVV
    else:
        # Clean CVV input
        clean_cvv = re.sub(r'\D', '', cvv)
        if is_amex:
            cvv_result = clean_cvv[:4] if len(clean_cvv) >= 4 else str(random.randint(1000, 9999))
        else:
            cvv_result = clean_cvv[:3] if len(clean_cvv) >= 3 else str(random.randint(100, 999))

    return f"{cc_result}|{mes}|{ano}|{cvv_result}"

# Bulk card generator with Luhn validation
async def luhn_card_genarator(cc, mes, ano, cvv, amount):
    all_cards = ""
    for _ in range(amount):
        while True:
            result = await cc_genarator(cc, mes, ano, cvv)
            ccx, mesx, anox, cvvx = result.split("|")
            check_luhn = await checkLuhn(ccx)
            if check_luhn:
                all_cards += f"{ccx}|{mesx}|{anox}|{cvvx}\n"
                break
    return all_cards

# Bin details function using CSV data
async def get_bin_details(bin_code):
    """Get BIN details from CSV data"""
    clean_bin = clean_bin_input(bin_code)
    
    # Try exact match first
    if clean_bin in bin_data:
        data = bin_data[clean_bin]
        country_name = get_country_name(data['country_code'])
        return (
            data['vendor'], 
            data['type'], 
            data['level'], 
            data['bank_name'], 
            country_name, 
            data['flag'], 
            "N/A"  # Currency not available in CSV
        )
    
    # Try partial match (shorter BINs)
    for length in range(len(clean_bin)-1, 4, -1):  # Try from longest to shortest
        partial_bin = clean_bin[:length]
        if partial_bin in bin_data:
            data = bin_data[partial_bin]
            country_name = get_country_name(data['country_code'])
            return (
                data['vendor'], 
                data['type'], 
                data['level'], 
                data['bank_name'], 
                country_name, 
                data['flag'], 
                "N/A"
            )
    
    # No match found
    return "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A"

# Generate the formatted message
def generate_response(cc, amount, all_cards, brand, type_, level, bank, country, flag, time_taken, user_name, user_id):
    cards_list = all_cards.strip().split('\n')
    cards_block = "\n".join([f"<code>{card}</code>" for card in cards_list])
    
    return f"""
- 𝐂𝐂 𝐆𝐞𝐧𝐞𝐫𝐚𝐭𝐞𝐝 𝐒𝐮𝐜𝐜𝐞𝐬𝐬𝐟𝐮𝐥𝐥𝐲
- 𝐁𝐢𝐧 - {cc}
- 𝐀𝐦𝐨𝐮𝐧𝐭 - {amount}
⋆——————✰◦✰◦✰——————⋆
{cards_block}
⋆——————✰◦✰◦✰——————⋆
- 𝗜𝗻𝗳𝗼 - {brand} - {type_} - {level}
- 𝐁𝐚𝐧𝐤 - {bank} 🏛
- 𝐂𝐨𝐮𝐧𝐭𝐫𝐲 - {country} - {flag}

- 𝐓𝐢𝐦𝐞: - {time_taken:0.2f} 𝐬𝐞𝐜𝐨𝐧𝐝𝐬
𝗚𝗲𝗻 𝗯𝘆 :  <a href="tg://user?id={user_id}"> {user_name}</a>
𝗢𝘄𝗻𝗲𝗿 :  <a href="https://t.me/spid_3r">&#8203;ッ</a>
"""

# Error logger
async def error_log(error_msg):
    print(f"Error: {error_msg}")

# Simple parameter encoding
def encode_params_simple(cc, mes, ano, cvv, amount, user_id):
    """Simple encoding with user ID"""
    # Use compact format: cc|mes|ano|cvv|amount|user_id
    clean_cc = clean_bin_input(cc)
    clean_mes = mes[:2] if mes != "None" else "00"
    clean_ano = ano[:4] if ano != "None" else "0000"
    clean_cvv = cvv[:4] if cvv != "None" else "0000"
    
    return f"{clean_cc}|{clean_mes}|{clean_ano}|{clean_cvv}|{amount}|{user_id}"

def decode_params_simple(encoded_params):
    """Decode simple encoded parameters"""
    try:
        parts = encoded_params.split("|")
        if len(parts) != 6:
            return None
            
        cc, mes, ano, cvv, amount, user_id = parts
        
        # Convert back to original format
        mes = mes if mes != "00" else "None"
        ano = ano if ano != "0000" else "None"
        cvv = cvv if cvv != "0000" else "None"
        amount = int(amount)
        
        return {
            'cc': cc,
            'mes': mes,
            'ano': ano,
            'cvv': cvv,
            'amount': amount,
            'user_id': user_id
        }
    except:
        return None

# Extract bin from replied message
def extract_bin_from_reply(message):
    """Extract BIN from replied message text"""
    if not message.reply_to_message or not message.reply_to_message.text:
        return None
    
    text = message.reply_to_message.text
    # Look for patterns like 447697, 447697|12, 447697|12|25, etc.
    patterns = [
        r'(\d{6,19})(?:\||\s|$)',
        r'(\d{6,19}\|\d{1,2})',
        r'(\d{6,19}\|\d{1,2}\|\d{2,4})',
        r'(\d{6,19}\|\d{1,2}\|\d{2,4}\|\d{3,4})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    
    return None

# Command handler for /gen and .gen
@app.on_message(filters.command("gen", [".", "/"]))
def multi(client, message):
    t1 = threading.Thread(target=bcall, args=(client, message))
    t1.start()

def bcall(client, message):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(gen_cmd(client, message))
    loop.close()

async def gen_cmd(client, message):
    try:
        user_id = str(message.from_user.id)
        user_name = message.from_user.first_name

        # Check if this is a reply to a message
        ccsdata = None
        if message.reply_to_message:
            ccsdata = extract_bin_from_reply(message)
        
        # If not a reply or couldn't extract from reply, use command arguments
        if not ccsdata:
            try:
                ccsdata = message.text.split()[1]
            except IndexError:
                # Format error message with hyperlinks
                resp = f"""
<a href='tg://user?id={user_id}'>〈〆〉</a>Spider 𝗮𝗹𝗴𝗼 -»>_

<a href='tg://user?id={user_id}'>〈北〉</a>Extra Invalid! ⚠

<a href='tg://user?id={user_id}'>╰┈➤</a> 𝙁𝙤𝙧𝙢𝙖𝙩 -» /gen 400022|10|2028
"""
                await message.reply_text(resp)
                return

        # Parse the BIN data
        cc_parts = ccsdata.split("|")
        cc = cc_parts[0]
        mes = cc_parts[1] if len(cc_parts) > 1 else "None"
        ano = cc_parts[2] if len(cc_parts) > 2 else "None"
        cvv = cc_parts[3] if len(cc_parts) > 3 else "None"

        # Clean and validate BIN
        clean_cc = clean_bin_input(cc)
        if not is_valid_bin(clean_cc[:6]):  # Check only first 6 digits for BIN validation
            resp = f"""
<a href='tg://user?id={user_id}'>(〆)</a> 𝗡𝗶𝗰𝗲 𝘁𝗿𝘆 𝗯𝘂𝗱𝗱𝘆.....
   
:(

<a href='tg://user?id={user_id}'>╰┈➤</a> 𝗜𝗻𝘃𝗮𝗹𝗶𝗱 𝗯𝗶𝗻 ⚠️
"""
            await message.reply_text(resp)
            return

        amount = 10  # Default amount
        try:
            amount = int(message.text.split()[2])
        except (IndexError, ValueError):
            pass

        # Check amount limit BEFORE sending "Generating..." message
        if amount > 10000:
            resp = """<b>Limit Reached ⚠️

Message: Maximum Generated Amount is 10K.</b>"""
            await message.reply_text(resp)
            return

        delete = await message.reply_text("<b>Generating...</b>")
        start = time.perf_counter()
        
        # Get BIN details from CSV (use first 6 digits for lookup)
        getbin = await get_bin_details(clean_cc[:6])
        brand, type_, level, bank, country, flag, currency = getbin

        all_cards = await luhn_card_genarator(cc, mes, ano, cvv, amount)
        time_taken = time.perf_counter() - start
        
        # Encode parameters for regen callback (with user ID)
        encoded_params = encode_params_simple(cc, mes, ano, cvv, amount, user_id)
        
        # Check if callback data is within Telegram limits (64 bytes)
        if len(f"regen_{encoded_params}") > 64:
            # If too large, don't include regen button
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("𝗗𝗼𝗻'𝘁 𝗽𝗿𝗲𝘀𝘀 🤧", callback_data="dontpress_button")],
                [InlineKeyboardButton("𝗘𝘅𝗶𝘁 ⚠️", callback_data=f"exit_{user_id}")]
            ])
        else:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("𝗥𝗲𝗴𝗲𝗻", callback_data=f"regen_{encoded_params}")],
                [InlineKeyboardButton("𝗗𝗼𝗻'𝘁 𝗽𝗿𝗲𝘀𝘀 🤧", callback_data="dontpress_button")],
                [InlineKeyboardButton("𝗘𝘅𝗶𝘁 ⚠️", callback_data=f"exit_{user_id}")]
            ])
        
        if amount <= 10:
            response_text = generate_response(
                cc, amount, all_cards, brand, type_, level, bank, 
                country, flag, time_taken, user_name, user_id
            )
            
            await client.delete_messages(message.chat.id, delete.id)
            await message.reply_text(response_text, reply_markup=keyboard, disable_web_page_preview=True)
        else:
            filename = f"{amount}x_CC_Generated_By_{user_id}.txt"
            with open(filename, "w") as f:
                f.write(all_cards)

            caption = f"""
- 𝐁𝐢𝐧: <code>{cc}</code> 
- 𝐀𝐦𝐨𝐮𝐧𝐭: {amount}

- 𝗜𝗻𝗳𝗼 - {brand} - {type_} - {level}
- 𝐁𝐚𝐧𝐤 - {bank} 🏛  
- 𝐂𝐨𝐮𝐧𝐭𝐫𝐲 - {country} - {flag} - {currency}

- 𝐓𝐢𝐦𝐞 - {time_taken:0.2f} 𝐬𝐞𝐜𝐨𝐧𝐝𝐬
𝗚𝗲𝗻 𝗯𝘆 :  <a href="tg://user?id={user_id}"> {user_name}</a>
𝗢𝘄𝗻𝗲𝗿 :  <a href="https://t.me/spid_3r">&#8203;ッ</a>
"""
            await client.delete_messages(message.chat.id, delete.id)
            # FIXED: Removed disable_web_page_preview parameter from reply_document
            await message.reply_document(
                document=filename, 
                caption=caption, 
                reply_to_message_id=message.id
            )
            os.remove(filename)

    except Exception as e:
        import traceback
        await error_log(traceback.format_exc())
        # Make sure to delete the "Generating..." message even on error
        try:
            await client.delete_messages(message.chat.id, delete.id)
        except:
            pass
        await message.reply_text("An error occurred while processing your request.")

# Track cooldown for regen button
regen_cooldown = {}

# Callback handler for buttons
@app.on_callback_query(filters.regex("^(regen_|exit_|dontpress_)"))
async def handle_callback(client, callback_query):
    try:
        # Handle the "Don't press" button first
        if callback_query.data == "dontpress_button":
            await callback_query.answer("( -_•)▄︻デ══━一 * * (- _ -)", show_alert=True)
            return
            
        action, data_param = callback_query.data.split("_", 1)
        user_id = str(callback_query.from_user.id)
        
        # Check cooldown for regen button (prevent rapid clicking)
        current_time = time.time()
        if action == "regen" and user_id in regen_cooldown:
            time_since_last = current_time - regen_cooldown[user_id]
            if time_since_last < 2:  # 2 second cooldown
                await callback_query.answer("Please wait a moment...", show_alert=False)
                return
        
        if action == "regen":
            # Set cooldown
            regen_cooldown[user_id] = current_time
            
            # Decode parameters from callback data
            params = decode_params_simple(data_param)
            if not params:
                await callback_query.answer("Invalid regeneration data!", show_alert=True)
                return
            
            # Check if the user who clicked is the same as the original user
            if user_id != params['user_id']:
                await callback_query.answer("〈Start your own /gen〉\n( -_•)▄︻デ══━一", show_alert=True)
                return
            
            # Validate BIN again
            clean_cc = clean_bin_input(params['cc'])
            if not is_valid_bin(clean_cc[:6]):
                await callback_query.answer("Invalid BIN!", show_alert=True)
                return
            
            # Acknowledge the callback immediately to prevent FloodWait
            await callback_query.answer("Regenerating cards...")
            
            # Generate new cards
            start = time.perf_counter()
            all_cards = await luhn_card_genarator(
                params['cc'], params['mes'], params['ano'], params['cvv'], params['amount']
            )
            time_taken = time.perf_counter() - start
            
            if params['amount'] <= 10:
                # Get BIN details again
                getbin = await get_bin_details(params['cc'][:6])
                brand, type_, level, bank, country, flag, currency = getbin
                
                response_text = generate_response(
                    params['cc'], params['amount'], all_cards, brand, type_, 
                    level, bank, country, flag, time_taken, 
                    callback_query.from_user.first_name, callback_query.from_user.id
                )
                
                # Re-encode parameters for next regen
                new_encoded_params = encode_params_simple(
                    params['cc'], params['mes'], params['ano'], params['cvv'], 
                    params['amount'], callback_query.from_user.id
                )
                
                # Check if callback data is within Telegram limits
                if len(f"regen_{new_encoded_params}") > 64:
                    keyboard = InlineKeyboardMarkup([
                        [InlineKeyboardButton("𝗗𝗼𝗻'𝘁 𝗽𝗿𝗲𝘀𝘀 🤧", callback_data="dontpress_button")],
                        [InlineKeyboardButton("𝗘𝘅𝗶𝘁 ⚠️", callback_data=f"exit_{callback_query.from_user.id}")]
                    ])
                else:
                    keyboard = InlineKeyboardMarkup([
                        [InlineKeyboardButton("𝗥𝗲𝗴𝗲𝗻", callback_data=f"regen_{new_encoded_params}")],
                        [InlineKeyboardButton("𝗗𝗼𝗻'𝘁 𝗽𝗿𝗲𝘀𝘀 🤧", callback_data="dontpress_button")],
                        [InlineKeyboardButton("𝗘𝘅𝗶𝘁 ⚠️", callback_data=f"exit_{callback_query.from_user.id}")]
                    ])
                
                # Always try to edit the message, allow rare card duplicates
                try:
                    await callback_query.message.edit_text(response_text, reply_markup=keyboard, disable_web_page_preview=True)
                except Exception as edit_error:
                    # If edit fails, just log the error but don't crash
                    print(f"Edit failed (non-critical): {edit_error}")
                    
            else:
                await callback_query.answer("Regen not available for large amounts!", show_alert=True)
                
        elif action == "exit":
            # Check if the user who clicked is the same as the original user
            if user_id != data_param:
                await callback_query.answer("〈Start your own /gen〉\n( -_•)▄︻デ══━一", show_alert=True)
                return
            
            # Delete the message
            await callback_query.message.delete()
            await callback_query.answer("Message deleted", show_alert=False)
            
    except Exception as e:
        import traceback
        await error_log(traceback.format_exc())
        await callback_query.answer("Error processing request!", show_alert=True)

# Run the bot
if __name__ == "__main__":
    # Load BIN data before starting the bot
    load_bin_data()
    print("Bot is running...")
    app.run()
