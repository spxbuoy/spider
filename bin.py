import csv
import pycountry
import re
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Your API credentials
API_ID = 28075471
API_HASH = "6db86d600105807f18519ebbb515d676"
BOT_TOKEN = "7534237564:AAEuRDGG9NP5Z8WkGS7zUYMwxTqAwMa2kq0"

# Initialize the Pyrogram Client
app = Client("bin_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

async def extract_bin(message):
    """Extract BIN from command or replied message"""
    try:
        # Check if it's a command with argument
        if message.text and len(message.text.split()) >= 2:
            bin_match = re.search(r'\b(\d{6,})\b', message.text.split()[1])
            if bin_match:
                return bin_match.group(1)
        
        # Check if it's a reply to a message
        if message.reply_to_message:
            reply_text = message.reply_to_message.text or message.reply_to_message.caption
            if reply_text:
                bin_match = re.search(r'\b(\d{6,})\b', reply_text)
                if bin_match:
                    return bin_match.group(1)
        
        return None
    except:
        return None

def get_bin_info_from_csv(fbin, csv_file='bins_all.csv'):
    try:
        with open(csv_file, mode='r', encoding='utf-8') as file:
            reader = csv.reader(file)
            for row in reader:
                if row[0] == fbin:
                    return {
                        "bin": row[0],
                        "country": row[1],
                        "flag": row[2],
                        "brand": row[3],
                        "type": row[4],
                        "level": row[5],
                        "bank": row[6]
                    }
    except Exception as e:
        print(f"Error reading CSV: {e}")
    return {}

def get_country_name(code, fallback_country_name):
    try:
        country = pycountry.countries.get(alpha_2=code)
        return country.name if country else fallback_country_name
    except Exception as e:
        print(f"Error getting country name: {e}")
        return fallback_country_name

@app.on_callback_query(filters.regex(r"^exit_bin_"))
async def handle_exit_button(client, callback_query):
    try:
        # Extract user ID from callback data
        data_parts = callback_query.data.split('_')
        original_user_id = int(data_parts[2])
        message_id = int(data_parts[3])
        
        # Check if the user clicking is the same as the original user
        if callback_query.from_user.id == original_user_id:
            # Delete the message silently
            await callback_query.message.delete()
            # Answer callback without any message
            await callback_query.answer()
        else:
            # Show alert to other users
            await callback_query.answer("⚠️ This is not your BIN check! Use /bin to check your own BIN.", show_alert=True)
            
    except Exception as e:
        # Answer silently even if error occurs
        await callback_query.answer()
        print(f"Error in callback: {e}")

@app.on_message(filters.command("bin", [".", "/"]))
async def cmd_bin(client, message):
    try:
        # Extract BIN from message
        bin_input = await extract_bin(message)
        
        if not bin_input:
            # Invalid BIN format - with hyperlinked symbols
            zero_symbol = f"<a href='tg://user?id={message.from_user.id}'>零</a>"
            north_symbol = f"<a href='tg://user?id={message.from_user.id}'>北</a>"
            jiu_symbol = f"<a href='tg://user?id={message.from_user.id}'>〆</a>"
            
            resp = f"""
〈{jiu_symbol}〉:(

〈{north_symbol}〉Invalid BIN! ⚠️

𝐌𝐞𝐬𝐬𝐚𝐠𝐞: 𝐍𝐨 𝐕𝐚𝐥𝐢𝐝 𝐁𝐈𝐍 𝐰𝐚𝐬 𝐟𝐨𝐮𝐧𝐝 𝐢𝐧 𝐲𝐨𝐮𝐫 𝐢𝐧𝐩𝐮𝐭.
"""
            await message.reply_text(resp, quote=True)
            return

        fbin = bin_input[:6]  # Take first 6 digits
        bin_info = get_bin_info_from_csv(fbin)

        if not bin_info:
            # BIN not found in database - with hyperlinked symbols
            zero_symbol = f"<a href='tg://user?id={message.from_user.id}'>零</a>"
            north_symbol = f"<a href='tg://user?id={message.from_user.id}'>北</a>"
            jiu_symbol = f"<a href='tg://user?id={message.from_user.id}'>〆</a>"
            
            resp = f"""
〈{jiu_symbol}〉:(

〈{north_symbol}〉Invalid BIN! ⚠️

𝐌𝐞𝐬𝐬𝐚𝐠𝐞: 𝐍𝐨 𝐕𝐚𝐥𝐢𝐝 𝐁𝐈𝐍 𝐢𝐧𝐟𝐨𝐫𝐦𝐚𝐭𝐢𝐨𝐧 𝐟𝐨𝐮𝐧𝐝 𝐢𝐧 𝐭𝐡𝐞 𝐝𝐚𝐭𝐚𝐛𝐚𝐬𝐞.
"""
            await message.reply_text(resp, quote=True)
            return

        # Format the response with hyperlinked symbols
        brand = bin_info.get("brand", "N/A").upper()
        card_type = bin_info.get("type", "N/A").upper()
        level = bin_info.get("level", "N/A").upper()
        bank = bin_info.get("bank", "N/A")
        country_code = bin_info.get("country", "N/A")
        flag = bin_info.get("flag", "")
        country_full_name = get_country_name(country_code, country_code).upper()
        
        # Create hyperlinked symbols
        zero_symbol = f"<a href='tg://user?id={message.from_user.id}'>零</a>"
        
        # Create user link (only one instance)
        user_link = f"<a href='tg://user?id={message.from_user.id}'>ª𝗺𝗸𝘂𝘀𝗵</a>"

        resp = f"""
〈{zero_symbol}〉𝘽𝙞𝙣 -» {fbin}
——————✵◦✵◦✵——————
〈{zero_symbol}〉𝙄𝙣𝙛𝙤 -» {brand} - {card_type} - {level}
〈{zero_symbol}〉𝘽𝙖𝙣𝙠 -» {bank}
〈{zero_symbol}〉𝘾𝙤𝙪𝙣𝙩𝙧𝙮 -» {country_full_name} {flag}
——————✵◦✵◦✵——————
〈{zero_symbol}〉𝘾𝙝𝙚𝙘𝙠𝙚𝙙 -» {user_link}
——————✵◦✵◦✵——————
"""

        # Create inline keyboard with Exit button
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "𝗘𝘅𝗶𝘁⚠️",
                        callback_data=f"exit_bin_{message.from_user.id}_{message.id}"
                    )
                ]
            ]
        )

        await message.reply_text(
            resp, 
            quote=True, 
            disable_web_page_preview=True,
            reply_markup=keyboard
        )

    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        print(f"Error in cmd_bin: {error_msg}")
        await message.reply_text("❌ An error occurred while processing your request.", quote=True)

if __name__ == "__main__":
    print("🤖 BIN Lookup Bot is starting...")
    print("Press Ctrl+C to stop the bot")
    app.run()
