import asyncio
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession as TelethonSession
from pyrogram import Client
from pyrogram.errors import SessionPasswordNeeded
from config import API_ID, API_HASH, BOT_TOKEN

bot = TelegramClient("bot", API_ID, API_HASH).start(bot_token=BOT_TOKEN)
user_data = {}

@bot.on(events.NewMessage(pattern="/start"))
async def start(event):
    buttons = [[Button.inline("⚡ Generate Session", b"generate")]]
    await event.respond("👋 **Welcome!**\n\nGenerate Pyrogram V2 or Telethon session easily!", buttons=buttons)

@bot.on(events.CallbackQuery)
async def callback_handler(event):
    user_id = event.sender_id
    if event.data == b"generate":
        buttons = [[Button.inline("⚡ Pyrogram V2", b"pyrogram"), Button.inline("💠 Telethon", b"telethon")]]
        await event.edit("🔹 **Choose Session Type:**", buttons=buttons)
    elif event.data in [b"pyrogram", b"telethon"]:
        user_data[user_id] = {"type": event.data.decode()}
        await bot.send_message(user_id, "✏️ **Enter your API ID:**")

@bot.on(events.NewMessage)
async def handle_input(event):
    user_id = event.sender_id
    if user_id not in user_data:
        return

    user_step = user_data[user_id]

    if "api_id" not in user_step:
        try:
            user_step["api_id"] = int(event.text)
            await bot.send_message(user_id, "✏️ **Enter your API Hash:**")
        except ValueError:
            await bot.send_message(user_id, "❌ Invalid API ID! Please enter a number.")

    elif "api_hash" not in user_step:
        user_step["api_hash"] = event.text
        await bot.send_message(user_id, "📱 **Enter your phone number with country code:**")

    elif "phone" not in user_step:
        user_step["phone"] = event.text
        await bot.send_message(user_id, "📩 Sending OTP...")

        if user_step["type"] == "pyrogram":
            user_step["client"] = Client("pyro_session", user_step["api_id"], user_step["api_hash"])
        else:
            user_step["client"] = TelegramClient(TelethonSession(), user_step["api_id"], user_step["api_hash"])

        client = user_step["client"]
        await client.connect()

        try:
            if user_step["type"] == "pyrogram":
                code_info = await client.send_code(user_step["phone"])
                user_step["phone_code_hash"] = code_info.phone_code_hash
            else:
                code_info = await client.send_code_request(user_step["phone"])
                user_step["phone_code_hash"] = code_info.phone_code_hash

            await bot.send_message(user_id, "🔢 **Enter the OTP received on Telegram:**")
        except Exception as e:
            await bot.send_message(user_id, f"❌ Error: {e}")

    elif "otp" not in user_step:
        user_step["otp"] = event.text
        client = user_step["client"]

        try:
            if user_step["type"] == "pyrogram":
                await client.sign_in(phone_number=user_step["phone"], phone_code=user_step["otp"], phone_code_hash=user_step["phone_code_hash"])
                session_string = await client.export_session_string()
            else:
                await client.sign_in(user_step["phone"], user_step["phone_code_hash"], user_step["otp"])
                session_string = client.session.save()

            await bot.send_message(user_id, f"✅ **Session Generated Successfully:**\n\n`{session_string}`")
            await client.disconnect()
            del user_data[user_id]

        except SessionPasswordNeeded:
            await bot.send_message(user_id, "🔒 **Enter your 2FA password:**")
            user_step["waiting_for_password"] = True  

        except Exception as e:
            await bot.send_message(user_id, f"❌ Error: {e}")

    elif "waiting_for_password" in user_step:
        password = event.text
        client = user_step["client"]

        try:
            await client.check_password(password)
            if user_step["type"] == "pyrogram":
                session_string = await client.export_session_string()
            else:
                session_string = client.session.save()

            await bot.send_message(user_id, f"✅ **Session Generated Successfully:**\n\n`{session_string}`")
            await client.disconnect()
            del user_data[user_id]

        except Exception as e:
            await bot.send_message(user_id, f"❌ Error: {e}")

print("Bot is running...")
bot.run_until_disconnected()
