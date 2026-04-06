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


# Snap-packaged Firefox paths (Ubuntu 22.04+)
_SNAP_FIREFOX_BINARY = "/snap/firefox/current/usr/lib/firefox/firefox-bin"
_SNAP_GECKODRIVER = "/snap/firefox/current/usr/lib/firefox/geckodriver"


def _is_snap_firefox() -> bool:
    """Return True if system firefox is a snap wrapper (not an ELF binary)."""
    system_firefox = shutil.which("firefox")
    if system_firefox is None:
        return False
    try:
        with open(system_firefox, "rb") as fh:
            return fh.read(4) != b"\x7fELF"
    except OSError:
        return False


def _resolve_firefox_binary() -> str | None:
    """Detect snap-packaged Firefox and return the real binary path.

    On Ubuntu, ``/usr/bin/firefox`` is often a shell-script wrapper
    installed by the ``firefox`` snap package.  Selenium cannot use a
    shell script as the browser binary and raises
    ``"binary is not a Firefox executable"``.

    Returns the path to the real binary inside the snap if found,
    or ``None`` when Firefox is installed natively.
    """
    if not _is_snap_firefox():
        return None

    # It's a script (snap wrapper).  Check for the real binary.
    if os.path.isfile(_SNAP_FIREFOX_BINARY) and os.access(_SNAP_FIREFOX_BINARY, os.X_OK):
        logger.debug("Detected snap Firefox – using binary at %s", _SNAP_FIREFOX_BINARY)
        return _SNAP_FIREFOX_BINARY

    logger.warning(
        "Firefox appears to be a snap wrapper but the expected binary "
        "was not found at %s",
        _SNAP_FIREFOX_BINARY,
    )
    return None


def _resolve_geckodriver() -> str | None:
    """Detect snap-packaged geckodriver and return the real ELF binary path.

    On Ubuntu with snap Firefox, ``/snap/bin/geckodriver`` is a wrapper
    that may fail when invoked from outside the snap sandbox.
    Returns the path to the real geckodriver inside the snap if found.
    """
    if not _is_snap_firefox():
        return None

    if os.path.isfile(_SNAP_GECKODRIVER) and os.access(_SNAP_GECKODRIVER, os.X_OK):
        logger.debug("Detected snap geckodriver – using %s", _SNAP_GECKODRIVER)
        return _SNAP_GECKODRIVER

    return None


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

    # Resolve snap-packaged Firefox if needed (Ubuntu 22.04+)
    snap_binary = _resolve_firefox_binary()
    if snap_binary:
        opts.binary_location = snap_binary

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
        # Use the real geckodriver binary from the snap if applicable
        snap_geckodriver = _resolve_geckodriver()
        service = FirefoxService(executable_path=snap_geckodriver) if snap_geckodriver else FirefoxService()
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
