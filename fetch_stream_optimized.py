#!/usr/bin/env python3
# Render-stable Selenium M3U8 extractor

import os
import sys
import time
import json
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# ================= CONFIG =================

TARGET_URL = os.getenv("TARGET_URL", "https://news.abplive.com/live-tv")
OUT_FILE = "m3u8.json"
MAX_WAIT_SECONDS = 20
POLL_INTERVAL = 0.6

# HARD FIX FOR RENDER
CHROME_BINARY = (
    os.getenv("CHROME_BIN")
    or "/usr/bin/chromium-browser"
    or "/usr/bin/google-chrome"
)

M3U8_RE = re.compile(
    r'https?://[^\'"\s>]+\.m3u8[^\'"\s>]*',
    re.IGNORECASE
)

# ================= UTILS =================

def now():
    return time.strftime("%H:%M:%S")

def write_json(urls):
    with open(OUT_FILE, "w") as f:
        json.dump({
            "updated_at": int(time.time()),
            "count": len(urls),
            "m3u8": sorted(urls)
        }, f, indent=2)

# ================= DRIVER =================

def make_driver():
    if not os.path.exists(CHROME_BINARY):
        print(f"❌ Chromium binary not found at {CHROME_BINARY}")
        sys.exit(1)

    options = Options()
    options.binary_location = CHROME_BINARY

    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-background-networking")
    options.add_argument("--no-first-run")
    options.add_argument("--disable-translate")

    options.set_capability(
        "goog:loggingPrefs",
        {"performance": "ALL"}
    )

    return webdriver.Chrome(options=options)

# ================= MAIN =================

def main():
    print(f"{now()} 🌀 Starting M3U8 extractor")
    print(f"{now()} Target URL: {TARGET_URL}")
    print(f"{now()} Using Chrome binary: {CHROME_BINARY}")

    driver = None
    found = set()
    seen = set()

    try:
        driver = make_driver()
        driver.set_page_load_timeout(30)

        try:
            driver.get(TARGET_URL)
        except Exception as e:
            print("⚠️ Page load warning:", e)

        time.sleep(2)

        start = time.time()
        while time.time() - start < MAX_WAIT_SECONDS:
            try:
                logs = driver.get_log("performance")
            except Exception:
                logs = []

            for entry in logs:
                raw = entry.get("message")
                if not raw or raw in seen:
                    continue
                seen.add(raw)

                try:
                    msg = json.loads(raw)["message"]
                except Exception:
                    continue

                method = msg.get("method", "")
                params = msg.get("params", {})

                if method == "Network.requestWillBeSent":
                    url = params.get("request", {}).get("url", "")
                    if ".m3u8" in url and url not in found:
                        found.add(url)
                        print("✅ FOUND:", url)

            if found:
                break

            time.sleep(POLL_INTERVAL)

        if found:
            write_json(found)
            print(f"🎉 Saved {len(found)} M3U8 URL(s)")
            sys.exit(0)

        print("⚠️ No M3U8 found")
        sys.exit(2)

    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass

if __name__ == "__main__":
    main()
