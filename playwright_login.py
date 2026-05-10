import json, time, os
from playwright.sync_api import sync_playwright

email = os.getenv("TERABOX_USER")
password = os.getenv("TERABOX_PASS")

def login_and_save_cookies():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu"
            ]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        print("Opening TeraBox login page...")
        page.goto("https://accounts.terabox.com/international/login", wait_until="networkidle", timeout=60000)
        time.sleep(3)

        print("Filling email...")
        page.wait_for_selector("input[name=loginemail]", timeout=30000)
        page.fill("input[name=loginemail]", email)
        time.sleep(1)

        print("Filling password...")
        page.wait_for_selector("input[name=loginpwd]", timeout=30000)
        page.fill("input[name=loginpwd]", password)
        time.sleep(1)

        print("Clicking submit...")
        page.click("button[type=submit]")

        print("Waiting for login to complete...")
        page.wait_for_load_state("networkidle", timeout=60000)
        time.sleep(8)

        cookies = context.cookies()
        if not cookies:
            print("WARNING: No cookies saved! Login may have failed.")
        else:
            json.dump(cookies, open("cookies.json", "w"))
            print(f"Cookies saved successfully! ({len(cookies)} cookies)")

        browser.close()

if __name__ == "__main__":
    login_and_save_cookies()
