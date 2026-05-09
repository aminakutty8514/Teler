from pyrogram import Client, filters
import requests, os

API_ID=12425668
API_HASH="d92ea6995790b6f2de53f52a80e14829"
BOT_TOKEN="8418626570:AAHNLgflmy1l-XEi6nNtR8N_5KbQWsfC0kA"

# Terabox cookies
COOKIES = {
    "ndus": "Yb2luXNpeHui2vcxAARd5hIYYKLZmvlvUxyBloD9",
    "csrfToken": "fBXdvQQTb-AoKpIaVzZafrZj",
    # Add other necessary cookie fields if required
}

app = Client("terabox_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)


def download_terabox(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers, cookies=COOKIES)
    filename = url.split("/")[-1]
    with open(filename, "wb") as f:
        f.write(r.content)
    return filename


@app.on_message(filters.private & filters.text)
def handle(client, message):
    url = message.text.strip()
    if "terabox" in url:
        msg = message.reply_text("Downloading…")
        try:
            file_path = download_terabox(url)
            message.reply_document(file_path)
            os.remove(file_path)
            msg.edit("✅ Done")
        except Exception as e:
            msg.edit(f"❌ Error: {e}")
    else:
        message.reply_text("Terabox link ayakkane da.")


app.run()
