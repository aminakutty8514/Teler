from pyrogram import Client
import os, json, requests

api_id = int(os.getenv("TELEGRAM_API_ID"))
api_hash = os.getenv("TELEGRAM_API_HASH")
bot_token = os.getenv("BOT_TOKEN")

app = Client("terabox_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

@app.on_message()
def handler(_, m):
    if "terabox.com" in m.text.lower():
        m.reply("⬇️ Terabox link received. Download processing... (demo setup)")

if __name__ == "__main__":
    app.run()
