"""Browser vision: capture webpage via remote Chrome."""
import base64
import os
from pathlib import Path
from urllib.parse import urlparse

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from libs.base_agent_action import BaseAgentAction
from libs.logger import log
from libs.remote_chrome_utils import dismiss_consent


class BrowserVisionAction(BaseAgentAction):
    """Capture webpage: screenshot, HTML, and body text."""

    PAGE_LOAD_TIMEOUT = 10
    MAX_SCREENSHOT_DIMENSION = 32767  # Chrome CDP limit
    DEFAULT_WIDTH = 800
    DEFAULT_HEIGHT = 1200

    def _error_result(self, url: str, error: str) -> dict:
        """Return error result with clear message."""
        return {
            "action": "_BROWSER_VISION",
            "url": url,
            "error": error,
            "status": "failed",
        }

    def execute(self):
        url = self.params.get("url", "").strip()
        if not url:
            return self._error_result("", "Missing or empty url parameter")
        if not self._is_valid_url(url):
            return self._error_result(url, f"Invalid URL: {url}")

        full_page = self.params.get("full_page", True)
        if isinstance(full_page, str):
            full_page = full_page.lower() in ("true", "1", "yes")

        headless = self.params.get("headless", False)
        if isinstance(headless, str):
            headless = headless.lower() in ("true", "1", "yes")

        width, height = self._parse_window_size()

        remote_driver = os.getenv("REMOTE_BROWSER_SERVER")
        if not remote_driver:
            return self._error_result(url, "REMOTE_BROWSER_SERVER not set in environment")

        options = self._build_chrome_options(headless, width, height)
        driver = None
        try:
            driver = webdriver.Remote(
                command_executor=remote_driver,
                options=options,
            )
            driver.set_page_load_timeout(self.PAGE_LOAD_TIMEOUT)
            driver.get(url)
            self._wait_for_page_ready(driver)
            dismiss_consent(driver)
            self._wait_for_page_ready(driver)

            output_dir = self.workspace / "output"
            output_dir.mkdir(parents=True, exist_ok=True)

            html = driver.page_source
            html_path = output_dir / "browser_vision.html"
            html_path.write_text(html, encoding="utf-8")

            screenshot = self._capture_screenshot(driver, full_page)
            png_path = output_dir / "browser_vision.png"
            png_path.write_bytes(screenshot)

            content = driver.find_element(By.TAG_NAME, "body").text
            txt_path = output_dir / "browser_vision.txt"
            txt_path.write_text(content, encoding="utf-8")

            return {
                "action": "_BROWSER_VISION",
                "url": url,
                "full_page": full_page,
                "headless": headless,
                "width": width,
                "height": height,
                "html": str(html_path),
                "screenshot": str(png_path),
                "content": str(txt_path),
                "follow_up": {
                    "name": "_LLM_SUMMARY",
                    "params": {"content": str(txt_path)},
                },
            }
        except TimeoutException:
            return self._error_result(url, f"Page load timeout ({self.PAGE_LOAD_TIMEOUT}s)")
        except WebDriverException as e:
            msg = str(e).split("\n")[0] if e else "Unknown WebDriver error"
            log(f"[BrowserVision] WebDriver error: {e}")
            return self._error_result(url, f"Browser error: {msg}")
        except Exception as e:
            log(f"[BrowserVision] Error: {e}")
            return self._error_result(url, f"Error: {e}")
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception as e:
                    log(f"[BrowserVision] Driver quit error: {e}")

    def _parse_window_size(self) -> tuple[int, int]:
        """Parse width and height from params. Default 1080x1650. Clamp to valid range."""
        width = self._to_int(self.params.get("width"), self.DEFAULT_WIDTH, 320, 3840)
        height = self._to_int(self.params.get("height"), self.DEFAULT_HEIGHT, 240, 7680)
        return (width, height)

    def _to_int(self, value, default: int, min_val: int, max_val: int) -> int:
        """Convert value to int, clamp to range, or return default if invalid."""
        if value is None:
            return default
        try:
            n = int(value)
            return max(min_val, min(max_val, n))
        except (ValueError, TypeError):
            return default

    def _build_chrome_options(self, headless: bool, width: int, height: int) -> webdriver.ChromeOptions:
        """Build Chrome options: headless, user-agent, language, performance tweaks."""
        options = webdriver.ChromeOptions()
        options.add_argument(f"--window-size={width},{height}")
        if headless:
            options.add_argument("--headless=new")
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        options.add_argument("--lang=en-US")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-popup-blocking")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        return options

    def _is_valid_url(self, url: str) -> bool:
        """Check if URL has valid scheme and netloc."""
        try:
            result = urlparse(url)
            return bool(result.scheme in ("http", "https") and result.netloc)
        except Exception:
            return False

    def _capture_screenshot(self, driver, full_page: bool) -> bytes:
        """Capture screenshot. Full-page via CDP when requested, else viewport."""
        if full_page:
            try:
                metrics = driver.execute_cdp_cmd("Page.getLayoutMetrics", {})
                content = metrics.get("contentSize", {})
                width = min(int(content.get("width", 1080)), self.MAX_SCREENSHOT_DIMENSION)
                height = min(int(content.get("height", 1650)), self.MAX_SCREENSHOT_DIMENSION)
                result = driver.execute_cdp_cmd("Page.captureScreenshot", {
                    "format": "png",
                    "captureBeyondViewport": True,
                    "clip": {"x": 0, "y": 0, "width": width, "height": height, "scale": 1},
                })
                if result and result.get("data"):
                    return base64.b64decode(result["data"])
            except Exception as e:
                log(f"[BrowserVision] Full-page capture failed, using viewport: {e}")
        return driver.get_screenshot_as_png()

    def _wait_for_page_ready(self, driver, timeout: int = None) -> None:
        """Wait for document.readyState == 'complete'. Returns immediately if already ready."""
        if timeout is None:
            timeout = self.PAGE_LOAD_TIMEOUT
        def ready(d):
            return d.execute_script("return document.readyState") == "complete"
        WebDriverWait(driver, timeout).until(ready)