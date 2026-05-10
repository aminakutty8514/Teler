from pyrogram import Client, filters
from pyrogram.errors import MessageNotModified
import os, requests, re, threading
from http.server import HTTPServer, BaseHTTPRequestHandler

api_id = int(os.getenv("TELEGRAM_API_ID"))
api_hash = os.getenv("TELEGRAM_API_HASH")
bot_token = os.getenv("BOT_TOKEN")

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running!")
    def log_message(self, *args):
        pass

def run_server():
    server = HTTPServer(("0.0.0.0", 10000), Handler)
    server.serve_forever()

threading.Thread(target=run_server, daemon=True).start()

app = Client("terabox_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

def extract_terabox_id(url):
    match = re.search(r'surl=([^&]+)', url)
    if match:
        return match.group(1)
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

        api_url = f"https://terabox.com/api/shorturlinfo?app_id=250528&shorturl={surl}&root=1"
        resp = requests.get(api_url, headers=headers, timeout=15)
        data = resp.json()

        if data.get("errno") != 0:
            return None, f"API Error {data.get('errno')}: {data.get('errmsg', 'Unknown error')}"

        file_list = data.get("list", [])
        if not file_list:
            return None, "No files found in this link"

        file = file_list[0]
        return {
            "name": file.get("server_filename"),
            "size": int(file.get("size", 0)),
            "dlink": file.get("dlink"),
        }, None

    except Exception as e:
        return None, f"Exception: {str(e)}"

def format_size(size):
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"

def safe_edit(msg, text):
    try:
        msg.edit(text, disable_web_page_preview=True)
    except MessageNotModified:
        pass

@app.on_message(filters.text)
def handler(_, m):
    if "terabox.com" not in m.text.lower() and "terabox.app" not in m.text.lower():
        return

    urls = re.findall(r'https?://[^\s]+terabox[^\s]+', m.text, re.IGNORECASE)
    if not urls:
        m.reply("❌ Valid TeraBox link കണ്ടെത്തിയില്ല.")
        return

    msg = m.reply("⏳ Processing your TeraBox link...")

    info, error = get_download_link(urls[0])

    if error:
        safe_edit(msg, f"❌ Failed: {error}")
        return

    text = (
        f"📁 **{info['name']}**\n"
        f"📦 Size: {format_size(info['size'])}\n\n"
        f"⬇️ [Download Link]({info['dlink']})"
    )
    safe_edit(msg, text)

if __name__ == "__main__":
    app.run()
