#!/usr/bin/env python3
# fetch_stream_optimized.py - Render compatible version
# Optimized for Render.com's container environment

import os
import sys
import time
import json
import re
import shutil
import subprocess
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

try:
    from webdriver_manager.chrome import ChromeDriverManager
    _HAS_WDM = True
except Exception:
    _HAS_WDM = False

DEFAULT_URL = "https://news.abplive.com/live-tv"
M3U8_RE = re.compile(r'https?://[^\'"\s>]+\.m3u8[^\'"\s>]*', flags=re.IGNORECASE)

def now():
    return time.strftime("%H:%M:%S")

def extract_m3u8_from_text(text):
    if not text:
        return []
    return M3U8_RE.findall(text)

def get_chrome_version():
    """Get Chrome version for Render environment"""
    # Render-specific chrome locations
    chrome_paths = [
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/usr/bin/chromium-browser",
        "/usr/bin/chromium",
    ]
    
    for path in chrome_paths:
        if os.path.exists(path):
            try:
                result = subprocess.run([path, "--version"], 
                                      capture_output=True, 
                                      text=True)
                if result.returncode == 0:
                    return result.stdout.strip()
            except Exception:
                continue
    
    # Fallback to which
    for cmd in ["google-chrome", "chromium-browser", "chromium"]:
        exe = shutil.which(cmd)
        if exe:
            try:
                result = subprocess.run([exe, "--version"], 
                                      capture_output=True, 
                                      text=True)
                return result.stdout.strip()
            except Exception:
                continue
    return "Chrome not found"

def setup_selenium():
    """Configure Selenium for Render environment"""
    options = Options()
    
    # Render-specific configuration
    options.binary_location = "/usr/bin/google-chrome-stable"  # Standard Render location
    
    # Headless configuration
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-background-networking")
    options.add_argument("--disable-default-apps")
    options.add_argument("--disable-features=Translate")
    options.add_argument("--disable-component-update")
    options.add_argument("--disable-background-timer-throttling")
    options.add_argument("--disable-renderer-backgrounding")
    options.add_argument("--disable-backgrounding-occluded-windows")
    options.add_argument("--disable-client-side-phishing-detection")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-prompt-on-repost")
    options.add_argument("--disable-domain-reliability")
    options.add_argument("--disable-sync")
    options.add_argument("--disable-breakpad")
    options.add_argument("--disable-ipc-flooding-protection")
    options.add_argument("--enable-automation")
    options.add_argument("--password-store=basic")
    options.add_argument("--use-mock-keychain")
    options.add_argument("--window-size=1280,720")
    options.add_argument("--log-level=3")
    
    # Performance optimizations
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--disable-features=VizDisplayCompositor")
    options.add_argument("--disable-features=AudioServiceOutOfProcess")
    options.add_argument("--disable-accelerated-2d-canvas")
    
    # Set experimental options
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_experimental_option("prefs", {
        "profile.default_content_setting_values.media_stream_mic": 1,
        "profile.default_content_setting_values.media_stream_camera": 1,
        "profile.default_content_setting_values.geolocation": 1,
        "profile.default_content_setting_values.notifications": 1,
        "profile.default_content_setting_values.images": 2,  # Allow images
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False,
    })
    
    # Set logging preferences
    options.set_capability("goog:loggingPrefs", {"performance": "ALL", "browser": "SEVERE"})
    
    # Get ChromeDriver - Render specific
    if os.path.exists("/usr/local/bin/chromedriver"):
        chromedriver_path = "/usr/local/bin/chromedriver"
    elif _HAS_WDM:
        try:
            # Use WDM with custom cache location
            os.environ['WDM_LOCAL'] = '1'
            chromedriver_path = ChromeDriverManager(
                cache_valid_range=30,
                path="/tmp/chromedriver"
            ).install()
        except Exception as e:
            print(f"{now()} WDM failed: {e}")
            chromedriver_path = None
    else:
        chromedriver_path = None
    
    print(f"{now()} ChromeDriver path: {chromedriver_path}")
    
    # Create service
    service_args = ["--verbose"]
    if chromedriver_path:
        service = Service(chromedriver_path, service_args=service_args)
    else:
        service = Service(service_args=service_args)
    
    # Create driver
    try:
        driver = webdriver.Chrome(service=service, options=options)
        
        # Set timeouts
        driver.set_page_load_timeout(30)
        driver.set_script_timeout(30)
        driver.implicitly_wait(5)
        
        # Execute CDP commands
        driver.execute_cdp_cmd("Network.enable", {})
        
        return driver
    except Exception as e:
        print(f"{now()} Failed to create driver: {e}")
        raise

def capture_stream_urls(driver, url, max_wait=15):
    """Capture m3u8 URLs from page"""
    found = set()
    processed = set()
    
    print(f"{now()} Navigating to: {url}")
    
    try:
        driver.get(url)
        print(f"{now()} Page loaded")
        
        # Allow some time for players to initialize
        time.sleep(2)
        
        start_time = time.time()
        poll_interval = 0.5
        
        while time.time() - start_time < max_wait:
            # Get performance logs
            try:
                logs = driver.get_log("performance")
            except Exception as e:
                print(f"{now()} Warning getting logs: {e}")
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
                
                # Check Network.requestWillBeSent
                if method == "Network.requestWillBeSent":
                    request = params.get("request", {})
                    url = request.get("url", "")
                    if ".m3u8" in url.lower() and url not in found:
                        found.add(url)
                        print(f"{now()} Found (request): {url}")
                
                # Check Network.responseReceived
                elif method == "Network.responseReceived":
                    response = params.get("response", {})
                    url = response.get("url", "")
                    
                    # Direct m3u8 URLs
                    if ".m3u8" in url.lower() and url not in found:
                        found.add(url)
                        print(f"{now()} Found (response): {url}")
                    
                    # Check response body for embedded m3u8 URLs
                    request_id = params.get("requestId")
                    if request_id and any(x in url.lower() for x in ['.json', '.js', '.txt', '.html', '.xml']):
                        try:
                            body_info = driver.execute_cdp_cmd(
                                "Network.getResponseBody",
                                {"requestId": request_id}
                            )
                            body = body_info.get("body", "")
                            if body and ".m3u8" in body:
                                matches = extract_m3u8_from_text(body)
                                for match in matches:
                                    if match not in found:
                                        found.add(match)
                                        print(f"{now()} Found (in body): {match}")
                        except Exception:
                            pass
            
            # Check page source as fallback
            if not found:
                try:
                    page_source = driver.page_source
                    matches = extract_m3u8_from_text(page_source)
                    for match in matches:
                        if match not in found:
                            found.add(match)
                            print(f"{now()} Found (in source): {match}")
                except Exception as e:
                    print(f"{now()} Warning checking source: {e}")
            
            # If we found URLs, we can exit early
            if found:
                break
            
            # Wait before next poll
            time.sleep(poll_interval)
        
        return found
    
    except Exception as e:
        print(f"{now()} Error during capture: {e}")
        return found

def main():
    """Main function optimized for Render"""
    # Get target URL
    target_url = os.getenv("TARGET_URL", "")
    if not target_url:
        if len(sys.argv) > 1:
            target_url = sys.argv[1]
        else:
            target_url = DEFAULT_URL
    
    print(f"{now()} Starting Render-optimized stream capture")
    print(f"{now()} Target URL: {target_url}")
    
    # Check Chrome availability
    chrome_version = get_chrome_version()
    print(f"{now()} Chrome version: {chrome_version}")
    
    # Setup and run
    driver = None
    try:
        driver = setup_selenium()
        print(f"{now()} Selenium initialized successfully")
        
        # Capture URLs
        urls = capture_stream_urls(
            driver=driver,
            url=target_url,
            max_wait=float(os.getenv("MAX_WAIT_SECONDS", "15"))
        )
        
        # Output results
        if urls:
            print(f"{now()} ✅ Success! Found {len(urls)} stream URL(s)")
            for url in sorted(urls):
                print(url)
            
            # For Render, we might want to output in a specific format
            # For API usage, you could output JSON
            if os.getenv("OUTPUT_JSON", "false").lower() == "true":
                print(json.dumps({"urls": list(urls)}, indent=2))
            
            sys.exit(0)
        else:
            print(f"{now()} ❌ No stream URLs found")
            sys.exit(1)
            
    except Exception as e:
        print(f"{now()} ❌ Critical error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(2)
        
    finally:
        if driver:
            try:
                driver.quit()
                print(f"{now()} Driver quit successfully")
            except Exception:
                pass

if __name__ == "__main__":
    main()
