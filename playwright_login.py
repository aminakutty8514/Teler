import json, time, os
from playwright.sync_api import sync_playwright

email = os.getenv("TERABOX_USER")
password = os.getenv("TERABOX_PASS")

def login_and_save_cookies():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://www.terabox.com")
        page.click("text=Log in")
        page.fill("input[name=loginemail]", email)
        page.fill("input[name=loginpwd]", password)
        page.click("button[type=submit]")
        time.sleep(8)
        cookies = page.context.cookies()
        json.dump(cookies, open("cookies.json", "w"))
        browser.close()

if __name__ == "__main__":
    login_and_save_cookies()
