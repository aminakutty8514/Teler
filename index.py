from pyrogram import Client, filters
import os, requests, re

api_id = int(os.getenv("TELEGRAM_API_ID"))
api_hash = os.getenv("TELEGRAM_API_HASH")
bot_token = os.getenv("BOT_TOKEN")

app = Client("terabox_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

def extract_terabox_id(url):
    # surl parameter extract ചെയ്യുക
    match = re.search(r'surl=([^&]+)', url)
    if match:
        return match.group(1)
    # /s/XXXX format
    match = re.search(r'/s/([a-zA-Z0-9_-]+)', url)
    if match:
        return match.group(1)
    return None

def get_download_link(url):
    try:
        surl = extract_terabox_id(url)
        if not surl:
            return None, "Invalid TeraBox link"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://www.terabox.com/",
        }

        # Public API - login വേണ്ട
        api_url = f"https://terabox.com/api/shorturlinfo?app_id=250528&shorturl={surl}&root=1"
        resp = requests.get(api_url, headers=headers, timeout=15)
        data = resp.json()

        if data.get("errno") != 0:
            return None, f"Error: {data.get('errmsg', 'Unknown error')}"

        file_list = data.get("list", [])
        if not file_list:
            return None, "No files found"

        file = file_list[0]
        return {
            "name": file.get("server_filename"),
            "size": int(file.get("size", 0)),
            "dlink": file.get("dlink"),
        }, None

    except Exception as e:
        return None, str(e)

def format_size(size):
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"

@app.on_message(filters.text)
def handler(_, m):
    if "terabox.com" in m.text.lower() or "terabox.app" in m.text.lower():
        # URL extract ചെയ്യുക
        urls = re.findall(r'https?://[^\s]+terabox[^\s]+', m.text, re.IGNORECASE)
        if not urls:
            m.reply("❌ Valid TeraBox link കണ്ടെത്തിയില്ല.")
            return

        msg = m.reply("⏳ Processing...")

        info, error = get_download_link(urls[0])

        if error:
            msg.edit(f"❌ Error: {error}")
            return

        text = (
            f"📁 **{info['name']}**\n"
            f"📦 Size: {format_size(info['size'])}\n\n"
            f"⬇️ [Download Link]({info['dlink']})"
        )
        msg.edit(text, disable_web_page_preview=True)

if __name__ == "__main__":
    app.run()
