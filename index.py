import os
import re
import asyncio
import logging
import requests
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
TERABOX_COOKIE = os.environ.get("TERABOX_COOKIE", "")
DOWNLOAD_DIR = "/tmp/downloads"
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
    "Referer": "https://www.1024terabox.com/",
}


async def safe_reply(message, text):
    """FloodWait handle ചെയ്ത് reply അയക്കുക"""
    while True:
        try:
            return await message.reply(text)
        except FloodWait as e:
            logger.warning("FloodWait: waiting %s seconds", e.value)
            await asyncio.sleep(e.value)


async def safe_edit(message, text):
    """FloodWait handle ചെയ്ത് message edit ചെയ്യുക"""
    while True:
        try:
            return await message.edit(text)
        except FloodWait as e:
            logger.warning("FloodWait: waiting %s seconds", e.value)
            await asyncio.sleep(e.value)
        except Exception:
            break


def extract_surl(url: str) -> str | None:
    patterns = [
        r"terabox\.com/s/([A-Za-z0-9_-]+)",
        r"1024terabox\.com/s/([A-Za-z0-9_-]+)",
        r"freeterabox\.com/s/([A-Za-z0-9_-]+)",
        r"[?&]surl=([A-Za-z0-9_-]+)",
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)
    return None


def get_share_info(surl: str) -> dict | None:
    api = f"https://www.1024terabox.com/api/shorturlinfo?shorturl={surl}&root=1"
    try:
        resp = requests.get(api, headers=HEADERS, timeout=15)
        data = resp.json()
        logger.info("shorturlinfo errno=%s", data.get("errno"))
        return data
    except Exception as e:
        logger.error("shorturlinfo failed: %s", e)
        return None


def get_file_list(shareid: str, uk: str, randsk: str) -> list | None:
    api = "https://www.1024terabox.com/share/list"
    params = {
        "app_id": "250528",
        "web": "1",
        "root": "1",
        "shareid": shareid,
        "uk": uk,
        "dir": "/",
        "order": "name",
        "desc": "0",
        "showempty": "0",
        "page": "1",
        "num": "20",
        "randsk": randsk,
    }
    try:
        resp = requests.get(api, headers=HEADERS, params=params, timeout=15)
        data = resp.json()
        logger.info("filelist errno=%s", data.get("errno"))
        if data.get("errno") != 0:
            logger.error("filelist error: %s", data)
            return None
        return data.get("list", [])
    except Exception as e:
        logger.error("filelist failed: %s", e)
        return None


def get_dlink(fs_id: str, shareid: str, uk: str, randsk: str, sign: str, timestamp: str) -> str | None:
    api = "https://www.1024terabox.com/api/download"
    params = {
        "app_id": "250528",
        "web": "1",
        "shareid": shareid,
        "uk": uk,
        "randsk": randsk,
        "sign": sign,
        "timestamp": timestamp,
        "fid_list": f"[{fs_id}]",
    }
    try:
        resp = requests.get(api, headers=HEADERS, params=params, timeout=15)
        data = resp.json()
        logger.info("dlink errno=%s", data.get("errno"))
        if data.get("errno") != 0:
            logger.error("dlink error: %s", data)
            return None
        return data["dlink"][0]["dlink"]
    except Exception as e:
        logger.error("dlink failed: %s", e)
        return None


def download_file(dlink: str, filename: str) -> str | None:
    save_path = os.path.join(DOWNLOAD_DIR, filename)
    try:
        with requests.get(
            dlink, headers=HEADERS, stream=True, timeout=120, allow_redirects=True
        ) as r:
            r.raise_for_status()
            with open(save_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=2 * 1024 * 1024):
                    if chunk:
                        f.write(chunk)
        return save_path
    except Exception as e:
        logger.error("Download failed: %s", e)
        return None


# ─── Handlers ────────────────────────────────

@app.on_message(filters.command("start"))
async def start(client: Client, message: Message):
    await safe_reply(
        message,
        "**👋 Terabox Downloader Bot**\n\n"
        "Terabox link അയക്കൂ, ഞാൻ download ചെയ്ത് തരാം!\n\n"
        "**Supported:**\n"
        "• terabox.com/s/...\n"
        "• 1024terabox.com/s/..."
    )


@app.on_message(filters.text & ~filters.command("start"))
async def handle_link(client: Client, message: Message):
    url = message.text.strip()

    if "terabox" not in url.lower():
        await safe_reply(message, "❌ Valid Terabox link അയക്കൂ.")
        return

    surl = extract_surl(url)
    if not surl:
        await safe_reply(message, "❌ Link-ൽ നിന്ന് ID കിട്ടിയില്ല.")
        return

    status = await safe_reply(message, "⏳ **File info നേടുന്നു...**")

    # Step 1
    info = get_share_info(surl)
    if not info:
        await safe_edit(status, "❌ Share info കിട്ടിയില്ല.")
        return

    shareid = str(info.get("shareid", ""))
    uk = str(info.get("uk", ""))
    randsk = info.get("randsk", "")
    sign = info.get("sign", "")
    timestamp = str(info.get("timestamp", ""))

    if not shareid or shareid == "0" or not uk:
        await safe_edit(status, "❌ Invalid share link.")
        return

    # Step 2
    await safe_edit(status, "⏳ **File list നേടുന്നു...**")
    files = get_file_list(shareid, uk, randsk)
    if not files:
        await safe_edit(status, "❌ File list കിട്ടിയില്ല.\nCookie expire ആയിട്ടുണ്ടാകും.")
        return

    file = files[0]
    filename = file.get("server_filename", "file")
    fs_id = str(file.get("fs_id", ""))
    size_bytes = int(file.get("size", 0))
    size_mb = round(size_bytes / (1024 * 1024), 2)

    await safe_edit(
        status,
        f"📁 **{filename}**\n"
        f"📦 Size: `{size_mb} MB`\n\n"
        f"⬇️ Download link നേടുന്നു..."
    )

    # Step 3
    dlink = get_dlink(fs_id, shareid, uk, randsk, sign, timestamp)
    if not dlink:
        await safe_edit(status, "❌ Download link കിട്ടിയില്ല.")
        return

    if size_bytes > 2 * 1024 * 1024 * 1024:
        await safe_edit(status, f"⚠️ File size ({size_mb} MB) 2GB limit കവിഞ്ഞു.")
        return

    await safe_edit(status, f"⬇️ **Downloading** `{filename}`...")

    local_path = download_file(dlink, filename)
    if not local_path:
        await safe_edit(status, "❌ Download failed.")
        return

    await safe_edit(status, "📤 **Uploading to Telegram...**")

    try:
        await message.reply_document(
            document=local_path,
            caption=f"✅ **{filename}**\n📦 `{size_mb} MB`",
            progress=upload_progress,
            progress_args=(status,),
        )
        await status.delete()
    except FloodWait as e:
        await asyncio.sleep(e.value)
    except Exception as e:
        await safe_edit(status, f"❌ Upload failed: {e}")
    finally:
        if os.path.exists(local_path):
            os.remove(local_path)


async def upload_progress(current, total, status_msg):
    percent = round((current / total) * 100)
    if percent % 25 == 0:
        try:
            await status_msg.edit(f"📤 Uploading... `{percent}%`")
        except Exception:
            pass


# ─── Run ─────────────────────────────────────

if __name__ == "__main__":
    logger.info("Bot starting...")
    app.run()
