import httpx
import asyncio
import time
from pyrogram import Client, filters

# Bot configuration
API_ID = 28075471
API_HASH = "6db86d600105807f18519ebbb515d676"
BOT_TOKEN = "8431590650:AAGLxFuABkY34arGY_EF5mb66Wgvr4dqzJc"

# Create Pyrogram client
app = Client("stripe_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Store valid SK keys (in memory, will be lost on restart)
valid_sks = []

async def addsk(sk):
    """Add a valid SK to the list if not already present"""
    if sk not in valid_sks:
        valid_sks.append(sk)
        print(f"Added SK to storage: {sk[:12]}...")

@app.on_message(filters.command("skinfo", [".", "/"]))
async def skinfo_command(client, message):
    try:
        start_time = time.time()
        
        # Extract SK from command or replied message
        sk = None
        if message.reply_to_message:
            # If replying to a message, extract SK from the replied message text
            replied_text = message.reply_to_message.text or message.reply_to_message.caption or ""
            # Simple extraction - look for sk_live_ pattern
            words = replied_text.split()
            for word in words:
                if word.startswith("sk_live_"):
                    sk = word
                    break
        else:
            # Extract from command arguments
            try:
                if len(message.command) > 1:
                    sk = message.command[1]
            except:
                pass
        
        # If no SK found
        if not sk:
            time_taken = round(time.time() - start_time, 4)
            user_link = f"<a href='tg://user?id={message.from_user.id}'>{message.from_user.first_name}</a>"
            
            resp = f"""〈<a href='tg://user?id={message.from_user.id}'>ア</a>〉 𝙎𝙠 -» sk_live_**

〈<a href='tg://user?id={message.from_user.id}'>カ</a>〉 𝙎𝙩𝙖𝙩𝙪𝙨 -» Dead! ❌
〈<a href='tg://user?id={message.from_user.id}'>ツ</a>〉 𝙍𝙚𝙨𝙪𝙡𝙩 -» Invalid API Key provided: sk_live_***

〈<a href='tg://user?id={message.from_user.id}'>꫟</a>〉     𝙏𝙞𝙢𝙚 -» {time_taken}'s

〈<a href='tg://user?id={message.from_user.id}'>ᥫ᭡</a>〉𝘾𝙝𝙚𝙘𝙠𝙚𝙙 𝙗𝙮 -» {user_link}"""
            
            await message.reply_text(resp)
            return

        session = httpx.AsyncClient()
        try:
            headers = {
                "Authorization": f"Bearer {sk}"
            }
            # Fetch SK info
            skinfo_response = await session.get("https://api.stripe.com/v1/account", headers=headers)
            skinfo = skinfo_response.json()

            # Fetch balance info
            balance_response = await session.get("https://api.stripe.com/v1/balance", headers=headers)
            balance_info = balance_response.json()
        except Exception as e:
            time_taken = round(time.time() - start_time, 4)
            user_link = f"<a href='tg://user?id={message.from_user.id}'>{message.from_user.first_name}</a>"
            
            resp = f"""〈<a href='tg://user?id={message.from_user.id}'>ア</a>〉 𝙎𝙠 -» {sk[:8]}xxxx

〈<a href='tg://user?id={message.from_user.id}'>カ</a>〉 𝙎𝙩𝙖𝙩𝙪𝙨 -» Dead! ❌
〈<a href='tg://user?id={message.from_user.id}'>ツ</a>〉 𝙍𝙚𝙨𝙪𝙡𝙩 -» Error fetching sk info
〈<a href='tg://user?id={message.from_user.id}'>ᥫ᭡</a>〉𝘾𝙝𝙚𝙘𝙠𝙚𝙙 𝙗𝙮 -» {user_link}"""
            
            await message.reply_text(resp)
            return
        finally:
            await session.aclose()

        # Check if the response contains error information
        if 'error' in skinfo:
            time_taken = round(time.time() - start_time, 4)
            user_link = f"<a href='tg://user?id={message.from_user.id}'>{message.from_user.first_name}</a>"
            
            resp = f"""〈<a href='tg://user?id={message.from_user.id}'>ア</a>〉 𝙎𝙠 -» {sk[:8]}xxxx

〈<a href='tg://user?id={message.from_user.id}'>カ</a>〉 𝙎𝙩𝙖𝙩𝙪𝙨 -» Dead! ❌
〈<a href='tg://user?id={message.from_user.id}'>ツ</a>〉 𝙍𝙚𝙨𝙪𝙡𝙩 -» {skinfo['error'].get('message', 'Unknown error')}
〈<a href='tg://user?id={message.from_user.id}'>꫟</a>〉     𝙏𝙞𝙢𝙚 -» {time_taken}'s

〈<a href='tg://user?id={message.from_user.id}'>ᥫ᭡</a>〉𝘾𝙝𝙚𝙘𝙠𝙚𝙙 𝙗𝙮 -» {user_link}"""
            
            await message.reply_text(resp)
            return

        charges_enabled = skinfo.get("charges_enabled", False)

        if charges_enabled:
            # If charges are enabled, call the addsk function
            await addsk(sk)

        url = skinfo.get("business_profile", {}).get("url", "N/A")
        name_data = skinfo.get("business_profile", {}).get("name", "N/A")
        currency = skinfo.get("default_currency", "N/A").upper()
        country = skinfo.get("country", "N/A")
        email = skinfo.get("email", "N/A")
        
        # Handle balance information safely
        available_balance = "N/A"
        pending_balance = "N/A"
        
        if balance_info and 'available' in balance_info and balance_info['available']:
            available_balance = balance_info['available'][0].get('amount', 'N/A')
            
        if balance_info and 'pending' in balance_info and balance_info['pending']:
            pending_balance = balance_info['pending'][0].get('amount', 'N/A')
            
        livemode = skinfo.get("livemode", False)
        
        time_taken = round(time.time() - start_time, 4)
        user_link = f"<a href='tg://user?id={message.from_user.id}'>{message.from_user.first_name}</a>"

        resp = f"""<b>SK Info Fetched Successfully ✅</b>
━━━━━━━━━━━━━━
🔑 <b>SK:</b> <code>{sk[:8]}xxxx</code>
🏢 <b>Name:</b> {name_data}
🌐 <b>Site Info:</b> {url}
🌍 <b>Country:</b> {country}
💱 <b>Currency:</b> {currency}
📧 <b>Email:</b> {email}
💰 <b>Balance Info:</b>
 [<a href='tg://user?id={message.from_user.id}'>カ</a>]  - Live Mode: {livemode}
  [<a href='tg://user?id={message.from_user.id}'>ツ</a>] - Charges Enabled: {charges_enabled}
  [<a href='tg://user?id={message.from_user.id}'>カ</a>] - Available Balance: {available_balance}
  [<a href='tg://user?id={message.from_user.id}'>㊄</a>] - Pending Balance: {pending_balance}
━━━━━━━━━━━━━━
〈<a href='tg://user?id={message.from_user.id}'>꫟</a>〉     𝙏𝙞𝙢𝙚 -» {time_taken}'s
<b>Checked By:</b> {user_link}
<b>Bot by:</b> <a href='tg://user?id=7738142451'>ツ</a>"""

        await message.reply_text(resp, disable_web_page_preview=True)

    except Exception as e:
        error_msg = f"Error: {str(e)}"
        await message.reply_text(f"An error occurred: {error_msg}")

# Start the bot
print("Starting Stripe SK Info Bot...")
print("Bot supports both /skinfo and .skinfo commands")
print("You can also reply to a message containing SK with /skinfo or .skinfo")
app.run()
