"""WebDriver factory – creates Chrome or Firefox drivers with BiDi support."""

from __future__ import annotations

import logging
import os
import shutil

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService

from config.settings import Settings
from models.exceptions import SessionCreationError
from models.session import BrowserType

logger = logging.getLogger("mcp_selenium.driver.factory")


def _real_firefox_binary() -> str | None:
    """Return the real Firefox binary path.

    On Ubuntu/snap, ``/usr/bin/firefox`` is a shell-script wrapper that
    geckodriver cannot launch directly.  When detected, return the real
    ELF binary path inside the snap package instead.
    """
    exe = shutil.which("firefox")
    if not exe:
        return None
    try:
        is_script = open(exe, "rb").read(4) != b"\x7fELF"
    except OSError:
        return None

    if not is_script:
        return exe  # Already a real binary, use as-is

    # Try common snap location
    snap_bin = "/snap/firefox/current/usr/lib/firefox/firefox-bin"
    if os.path.isfile(snap_bin):
        logger.debug("Detected snap Firefox wrapper — using %s", snap_bin)
        return snap_bin

    return None  # Can't resolve, let Selenium try on its own


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

    if settings.bidi_enabled:
        opts.set_capability("webSocketUrl", True)

    opts.set_capability(
        "goog:loggingPrefs",
        {"performance": "ALL", "browser": "ALL"},
    )

    try:
        driver = webdriver.Chrome(service=ChromeService(), options=opts)
        driver.set_page_load_timeout(settings.page_load_timeout)
        driver.set_script_timeout(settings.script_timeout)
        driver.implicitly_wait(settings.implicit_wait)
        logger.debug("Chrome driver created (headless=%s, bidi=%s)", use_headless, settings.bidi_enabled)
        return driver
    except Exception as exc:
        raise SessionCreationError(f"Failed to create Chrome driver: {exc}") from exc


def build_firefox_driver(settings: Settings, headless: bool | None = None) -> webdriver.Firefox:
    """Instantiate a Firefox WebDriver.

    Geckodriver is auto-resolved by Selenium Manager (4.6+).
    On snap-based systems the real Firefox binary is detected automatically.
    """
    opts = FirefoxOptions()

    real_bin = _real_firefox_binary()
    if real_bin:
        opts.binary_location = real_bin

    use_headless = settings.headless if headless is None else headless
    if use_headless:
        opts.add_argument("--headless")

    if settings.bidi_enabled:
        opts.set_capability("webSocketUrl", True)

    w, h = settings.window_size
    opts.add_argument(f"--width={w}")
    opts.add_argument(f"--height={h}")

    try:
        driver = webdriver.Firefox(service=FirefoxService(), options=opts)
        driver.set_page_load_timeout(settings.page_load_timeout)
        driver.set_script_timeout(settings.script_timeout)
        driver.implicitly_wait(settings.implicit_wait)
        logger.debug("Firefox driver created (headless=%s, bidi=%s)", use_headless, settings.bidi_enabled)
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
