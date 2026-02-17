import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

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