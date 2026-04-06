"""WebDriver factory – creates Chrome or Firefox drivers with BiDi support."""

from __future__ import annotations

import logging

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService

from config.settings import Settings
from models.exceptions import SessionCreationError
from models.session import BrowserType

logger = logging.getLogger("selenium_mcp.driver.factory")


def build_chrome_driver(settings: Settings, headless: bool | None = None) -> webdriver.Chrome:
    """Instantiate a Chrome WebDriver with BiDi and CDP options."""
    opts = ChromeOptions()

    use_headless = settings.headless if headless is None else headless
    if use_headless:
        opts.add_argument("--headless=new")

    w, h = settings.window_size
    opts.add_argument(f"--window-size={w},{h}")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--disable-extensions")
    opts.add_argument("--log-level=3")

    # Enable BiDi
    if settings.bidi_enabled:
        opts.set_capability("webSocketUrl", True)

    # Enable performance logging via CDP
    opts.set_capability(
        "goog:loggingPrefs",
        {"performance": "ALL", "browser": "ALL"},
    )

    try:
        service = ChromeService()
        driver = webdriver.Chrome(service=service, options=opts)
        driver.set_page_load_timeout(settings.page_load_timeout)
        driver.set_script_timeout(settings.script_timeout)
        driver.implicitly_wait(settings.implicit_wait)
        logger.debug(
            "Chrome driver created (headless=%s, bidi=%s)",
            use_headless, settings.bidi_enabled,
        )
        return driver
    except Exception as exc:
        raise SessionCreationError(f"Failed to create Chrome driver: {exc}") from exc


def build_firefox_driver(settings: Settings, headless: bool | None = None) -> webdriver.Firefox:
    """Instantiate a Firefox WebDriver with BiDi support."""
    opts = FirefoxOptions()

    use_headless = settings.headless if headless is None else headless
    if use_headless:
        opts.add_argument("--headless")

    # Enable BiDi
    if settings.bidi_enabled:
        opts.set_capability("webSocketUrl", True)

    w, h = settings.window_size
    opts.add_argument(f"--width={w}")
    opts.add_argument(f"--height={h}")

    try:
        service = FirefoxService()
        driver = webdriver.Firefox(service=service, options=opts)
        driver.set_page_load_timeout(settings.page_load_timeout)
        driver.set_script_timeout(settings.script_timeout)
        driver.implicitly_wait(settings.implicit_wait)
        logger.debug(
            "Firefox driver created (headless=%s, bidi=%s)",
            use_headless, settings.bidi_enabled,
        )
        return driver
    except Exception as exc:
        raise SessionCreationError(f"Failed to create Firefox driver: {exc}") from exc


def build_driver(
    browser: BrowserType,
    settings: Settings,
    headless: bool | None = None,
) -> webdriver.Remote:
    """Dispatch to the correct browser factory."""
    if browser == BrowserType.CHROME:
        return build_chrome_driver(settings, headless)
    if browser == BrowserType.FIREFOX:
        return build_firefox_driver(settings, headless)
    raise SessionCreationError(f"Unsupported browser: {browser!r}")
