import os
import re
import logging
import requests
from pyrogram import Client, filters
from pyrogram.types import Message

# ─────────────────────────────────────────────
# CONFIG — Environment variables ആയി set ചെയ്യുക (Render dashboard-ൽ)
# ─────────────────────────────────────────────
API_ID = int(os.environ.get("API_ID", 0))          # my.telegram.org-ൽ നിന്ന്
API_HASH = os.environ.get("API_HASH", "")          # my.telegram.org-ൽ നിന്ന്
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")        # @BotFather-ൽ നിന്ന്
TERABOX_COOKIE = os.environ.get("TERABOX_COOKIE", "")  # Browser-ൽ നിന്ന് copy ചെയ്തത്
DOWNLOAD_DIR = "/tmp/downloads"                    # Render-ൽ /tmp use ചെയ്യുക
# ─────────────────────────────────────────────

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

app = Client(
    "terabox_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
)

HEADERS = {
    "Cookie": TERABOX_COOKIE,
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.terabox.com/",
}


def extract_share_id(url: str) -> str | None:
    patterns = [
        r"terabox\.com/s/([A-Za-z0-9_-]+)",
        r"terabox\.com/sharing/link\?surl=([A-Za-z0-9_-]+)",
        r"1024terabox\.com/s/([A-Za-z0-9_-]+)",
        r"freeterabox\.com/s/([A-Za-z0-9_-]+)",
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)
    return None


def get_file_info(share_id: str) -> dict | None:
    api_url = f"https://www.terabox.com/api/shorturlinfo?shorturl={share_id}"
    try:
        resp = requests.get(api_url, headers=HEADERS, timeout=15)
        data = resp.json()
        if data.get("errno") != 0:
            logger.error("Terabox error: %s", data)
            return None
        return data
    except Exception as e:
        logger.error("API error: %s", e)
        return None


def download_file(dlink: str, filename: str) -> str | None:
    save_path = os.path.join(DOWNLOAD_DIR, filename)
    try:
        with requests.get(dlink, headers=HEADERS, stream=True, timeout=120) as r:
            r.raise_for_status()
            with open(save_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=2 * 1024 * 1024):
                    if chunk:
                        f.write(chunk)
        return save_path
    except Exception as e:
        logger.error("Download error: %s", e)
        return None


# ─── Handlers ────────────────────────────────

@app.on_message(filters.command("start"))
async def start(client: Client, message: Message):
    await message.reply(
        "**👋 Terabox Downloader Bot**\n\n"
        "Terabox link അയക്കൂ, ഞാൻ download ചെയ്ത് തരാം!\n\n"
        "**Supported links:**\n"
        "• terabox.com/s/...\n"
        "• 1024terabox.com/s/...\n"
        "• freeterabox.com/s/..."
    )


@app.on_message(filters.text & ~filters.command("start"))
async def handle_link(client: Client, message: Message):
    url = message.text.strip()

    if "terabox" not in url.lower():
        await message.reply("❌ Valid Terabox link അയക്കൂ.")
        return

    share_id = extract_share_id(url)
    if not share_id:
        await message.reply("❌ Link-ൽ നിന്ന് Share ID കിട്ടിയില്ല.")
        return

    status = await message.reply("⏳ **File info നേടുന്നു...**")

    info = get_file_info(share_id)
    if not info:
        await status.edit(
            "❌ **Error!**\nTerabox-ൽ നിന്ന് info കിട്ടിയില്ല.\n"
            "Cookie expire ആയിട്ടുണ്ടാകും."
        )
        return

    try:
        file_info = info["list"][0]
        filename = file_info["server_filename"]
        dlink = file_info["dlink"]
        size_bytes = int(file_info.get("size", 0))
        size_mb = round(size_bytes / (1024 * 1024), 2)
    except (KeyError, IndexError) as e:
        await status.edit(f"❌ Parse error: {e}")
        return

    await status.edit(
        f"📁 **{filename}**\n"
        f"📦 Size: `{size_mb} MB`\n\n"
        f"⬇️ Downloading..."
    )

    # 2GB limit (Pyrogram bot limit)
    if size_bytes > 2 * 1024 * 1024 * 1024:
        await status.edit(
            f"⚠️ File size ({size_mb} MB) 2GB limit കവിഞ്ഞു."
        )
        return

    local_path = download_file(dlink, filename)
    if not local_path:
        await status.edit("❌ Download failed. പിന്നീട് try ചെയ്യൂ.")
        return

    await status.edit("📤 **Uploading to Telegram...**")

    try:
        await message.reply_document(
            document=local_path,
            caption=f"✅ **{filename}**\n📦 `{size_mb} MB`",
            progress=upload_progress,
            progress_args=(status,),
        )
        await status.delete()
    except Exception as e:
        await status.edit(f"❌ Upload failed: {e}")
    finally:
        if os.path.exists(local_path):
            os.remove(local_path)


async def upload_progress(current, total, status_msg):
    percent = round((current / total) * 100)
    if percent % 20 == 0:  # 20% step-ൽ update
        try:
            await status_msg.edit(f"📤 Uploading... `{percent}%`")
        except Exception:
            pass


# ─── Run ─────────────────────────────────────

if __name__ == "__main__":
    logger.info("Bot starting with Pyrogram...")
    app.run()
