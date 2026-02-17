#!/usr/bin/env python3

"""
Capture a URL in the remote browser and save as eye.png to ../output.
Usage: python internet_eye.py "URL"
Example: python internet_eye.py "https://www.google.com"
"""
import sys
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

REMOTE_DRIVER = "http://192.168.1.153:4444"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
OUTPUT_FILE = OUTPUT_DIR / "eye.png"

# Text to click to dismiss cookie/consent (order matters: try "Accept all" before "Accept")
CONSENT_BUTTON_TEXTS = (
    "Accept all",
    "Accept All",
    "I agree",
    "I agree",
    "Agree",
    "Allow all",
    "Allow All",
    "Accept",
    "OK",
    "Got it",
    "Consent",
)


def dismiss_consent(driver: webdriver.Remote, wait_sec: float = 2.0) -> None:
    """Try to click a cookie/consent accept button so the screenshot is clean."""
    time.sleep(wait_sec)
    for text in CONSENT_BUTTON_TEXTS:
        try:
            # Main page: button or link with this text
            btn = WebDriverWait(driver, 2).until(
                EC.element_to_be_clickable((By.XPATH, f"//button[contains(., '{text}')] | //a[contains(., '{text}')] | //*[@role='button' and contains(., '{text}')]"))
            )
            btn.click()
            time.sleep(0.8)
            return
        except Exception:
            continue
    # Google: consent can be in an iframe
    try:
        consent_frame = driver.find_elements(By.CSS_SELECTOR, "iframe[src*='consent']")
        if consent_frame:
            driver.switch_to.frame(consent_frame[0])
            for text in CONSENT_BUTTON_TEXTS:
                try:
                    btn = driver.find_element(By.XPATH, f"//button[contains(., '{text}')] | //span[contains(., '{text}')]/ancestor::button")
                    btn.click()
                    time.sleep(0.8)
                    return
                except Exception:
                    continue
    except Exception:
        pass
    finally:
        try:
            driver.switch_to.default_content()
        except Exception:
            pass


def main() -> None:
    if len(sys.argv) < 2 or not sys.argv[1].strip():
        print("Usage: python internet_eye.py \"URL\"", file=sys.stderr)
        sys.exit(1)

    url = sys.argv[1].strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    options = webdriver.ChromeOptions()
    options.add_argument("--window-size=1080,1650")
    driver = webdriver.Remote(
        command_executor=REMOTE_DRIVER,
        options=options,
    )
    try:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        driver.get(url)
        dismiss_consent(driver)
        time.sleep(3)  # Let the page stabilize before screenshot
        driver.save_screenshot(str(OUTPUT_FILE))
        print(OUTPUT_FILE)
    finally:
        driver.quit()


if __name__ == "__main__":
    main()