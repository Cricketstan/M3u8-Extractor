
#!/usr/bin/env python3
import os, sys, time, json, re, shutil, subprocess
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

M3U8_RE = re.compile(r'https?://[^\'"\s>]+\.m3u8[^\'"\s>]*', re.I)
TARGET_URL = os.getenv("TARGET_URL", "https://news.abplive.com/live-tv")
OUT_FILE = "m3u8.json"

def now():
    return time.strftime("%H:%M:%S")

def extract(text):
    return M3U8_RE.findall(text or "")

def write_json(urls):
    with open(OUT_FILE, "w") as f:
        json.dump({
            "updated_at": int(time.time()),
            "count": len(urls),
            "m3u8": sorted(urls)
        }, f, indent=2)

def driver():
    opt = Options()
    opt.add_argument("--headless=new")
    opt.add_argument("--no-sandbox")
    opt.add_argument("--disable-dev-shm-usage")
    opt.add_argument("--disable-gpu")
    opt.add_argument("--disable-extensions")
    opt.set_capability("goog:loggingPrefs", {"performance": "ALL"})
    return webdriver.Chrome(service=Service("/usr/bin/chromedriver"), options=opt)

d = driver()
print(f"{now()} Loading {TARGET_URL}")
d.get(TARGET_URL)
time.sleep(2)

found, seen = set(), set()
start = time.time()

while time.time() - start < 20:
    for e in d.get_log("performance"):
        msg = json.loads(e["message"])["message"]
        if msg["method"] == "Network.requestWillBeSent":
            url = msg["params"]["request"]["url"]
            if ".m3u8" in url and url not in found:
                found.add(url)
                print("FOUND:", url)
    if found:
        break
    time.sleep(0.5)

d.quit()

if found:
    write_json(found)
    print("Saved m3u8.json")
    sys.exit(0)

print("No m3u8 found")
sys.exit(2)
