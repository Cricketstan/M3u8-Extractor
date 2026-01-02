#!/usr/bin/env python3
# fetch_stream_optimized.py
# Render-safe Selenium + CDP M3U8 extractor

import os
import sys
import time
import json
import re
import shutil
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# ================= CONFIG =================

TARGET_URL = os.getenv("TARGET_URL", "https://news.abplive.com/live-tv")
OUT_FILE = "m3u8.json"
MAX_WAIT_SECONDS = int(os.getenv("MAX_WAIT_SECONDS", "20"))
POLL_INTERVAL = 0.6

M3U8_RE = re.compile(
    r'https?://[^\'"\s>]+\.m3u8[^\'"\s>]*',
    re.IGNORECASE
)

# ================= UTILS =================

def now():
    return time.strftime("%H:%M:%S")

def extract_m3u8(text):
    if not text:
        return []
    return M3U8_RE.findall(text)

def write_json(urls):
    data = {
        "updated_at": int(time.time()),
        "count": len(urls),
        "m3u8": sorted(urls)
    }
    with open(OUT_FILE, "w") as f:
        json.dump(data, f, indent=2)

# ================= DRIVER =================

def make_driver():
    chrome_bin = (
        shutil.which("chromium")
        or shutil.which("chromium-browser")
        or shutil.which("google-chrome")
    )

    if not chrome_bin:
        print("❌ Chromium not found in PATH")
        sys.exit(1)

    options = Options()
    options.binary_location = chrome_bin

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

    driver = None
    found = set()
    processed = set()

    try:
        driver = make_driver()
        driver.set_page_load_timeout(30)

        print(f"{now()} Opening page...")
        try:
            driver.get(TARGET_URL)
        except Exception as e:
            print(f"{now()} ⚠️ Page load warning:", e)

        time.sleep(2)

        start = time.time()

        while time.time() - start < MAX_WAIT_SECONDS:
            try:
                logs = driver.get_log("performance")
            except Exception:
                logs = []

            for entry in logs:
                raw = entry.get("message")
                if not raw or raw in processed:
                    continue

                processed.add(raw)

                try:
                    msg = json.loads(raw)["message"]
                except Exception:
                    continue

                method = msg.get("method", "")
                params = msg.get("params", {})

                # Network requests
                if method == "Network.requestWillBeSent":
                    url = params.get("request", {}).get("url", "")
                    if ".m3u8" in url.lower() and url not in found:
                        found.add(url)
                        print(f"{now()} ✅ FOUND (request): {url}")

                # Network responses
                elif method == "Network.responseReceived":
                    resp = params.get("response", {})
                    url = resp.get("url", "")
                    mime = (resp.get("mimeType") or "").lower()

                    if ".m3u8" in url.lower() and url not in found:
                        found.add(url)
                        print(f"{now()} ✅ FOUND (response): {url}")

                    # Check body for embedded m3u8
                    if any(x in mime for x in ("json", "javascript", "text", "html")):
                        req_id = params.get("requestId")
                        if req_id:
                            try:
                                body = driver.execute_cdp_cmd(
                                    "Network.getResponseBody",
                                    {"requestId": req_id}
                                )
                                text = body.get("body", "")
                                for m in extract_m3u8(text):
                                    if m not in found:
                                        found.add(m)
                                        print(f"{now()} ✅ FOUND (body): {m}")
                            except Exception:
                                pass

            if found:
                break

            time.sleep(POLL_INTERVAL)

        if found:
            write_json(found)
            print(f"{now()} 🎉 Saved {len(found)} M3U8 URL(s) to {OUT_FILE}")
            sys.exit(0)
        else:
            print(f"{now()} ⚠️ No M3U8 found")
            sys.exit(2)

    finally:
        if driver:
            try:
                driver.quit()
                print(f"{now()} Driver closed")
            except Exception:
                pass

# ================= ENTRY =================

if __name__ == "__main__":
    main()
