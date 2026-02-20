"""Browser vision: capture webpage via remote Chrome."""
import os
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By

from libs.base_agent_action import BaseAgentAction
from libs.remote_chrome_utils import dismiss_consent


class BrowserVisionAction(BaseAgentAction):
    """Capture webpage: screenshot, HTML, and body text."""

    def execute(self):
        url = self.params["url"]
        remote_driver = os.getenv("REMOTE_BROWSER_SERVER")
        options = webdriver.ChromeOptions()
        options.add_argument("--window-size=1080,1650")
        driver = webdriver.Remote(
            command_executor=remote_driver,
            options=options,
        )
        try:
            driver.get(url)
            dismiss_consent(driver)
            time.sleep(3)

            output_dir = self.workspace / "output"
            output_dir.mkdir(parents=True, exist_ok=True)

            html = driver.page_source
            html_path = output_dir / "browser_vision.html"
            html_path.write_text(html, encoding="utf-8")

            screenshot = driver.get_screenshot_as_png()
            png_path = output_dir / "browser_vision.png"
            png_path.write_bytes(screenshot)

            content = driver.find_element(By.TAG_NAME, "body").text
            txt_path = output_dir / "browser_vision.txt"
            txt_path.write_text(content, encoding="utf-8")
        finally:
            driver.quit()

        return {
            "action": "_BROWSER_VISION",
            "url": url,
            "html": str(html_path),
            "screenshot": str(png_path),
            "content": str(txt_path),
            "follow_up": {
                "name": "_LLM_SUMMARY",
                "params": {"content": str(txt_path)},
            },
        }
