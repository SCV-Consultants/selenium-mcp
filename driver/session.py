"""Browser session wrapper – owns a single WebDriver instance."""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException as SeleniumTimeoutException,
    WebDriverException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from config.settings import Settings
from models.exceptions import (
    ElementInteractionError,
    ElementNotFoundError,
    NavigationError,
    ScreenshotError,
    ScriptExecutionError,
    TimeoutError as MCPTimeoutError,
)
from models.network import ConsoleLog, NetworkLog, PerformanceMetrics
from models.session import BrowserType, SessionInfo, SessionStatus

if TYPE_CHECKING:
    from events.dispatcher import EventDispatcher

logger = logging.getLogger("selenium_mcp.driver.session")


class BrowserSession:
    """
    Wraps a single Selenium WebDriver instance.

    Responsibilities:
    - Lifecycle management (create / close)
    - High-level browser actions (navigate, click, type, …)
    - Collection of logs (console, network, performance)
    - Retry logic for flaky interactions
    """

    def __init__(
        self,
        driver: WebDriver,
        browser: BrowserType,
        settings: Settings,
        dispatcher: "EventDispatcher",
        headless: bool,
    ) -> None:
        self._driver = driver
        self._settings = settings
        self._dispatcher = dispatcher

        self._session_id: str = str(uuid.uuid4())
        self._info = SessionInfo(
            session_id=self._session_id,
            browser=browser,
            headless=headless,
            status=SessionStatus.READY,
        )

        self._network_logs: List[NetworkLog] = []
        self._console_logs: List[ConsoleLog] = []
        self._intercept_patterns: List[str] = []

        logger.info("Session %s ready (%s, headless=%s)", self._session_id, browser.value, headless)

    # ------------------------------------------------------------------ #
    # Properties
    # ------------------------------------------------------------------ #

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def info(self) -> SessionInfo:
        self._info.current_url = self._safe_current_url()
        return self._info

    @property
    def driver(self) -> WebDriver:
        return self._driver

    # ------------------------------------------------------------------ #
    # Navigation
    # ------------------------------------------------------------------ #

    def open_page(self, url: str) -> None:
        """Navigate to *url* and wait for the page to load."""
        logger.debug("[%s] open_page(%s)", self._session_id, url)
        try:
            self._driver.get(url)
            self._info.current_url = url
        except WebDriverException as exc:
            raise NavigationError(f"Failed to open {url!r}: {exc}", self._session_id) from exc

    def navigate_back(self) -> None:
        try:
            self._driver.back()
        except WebDriverException as exc:
            raise NavigationError(f"navigate_back failed: {exc}", self._session_id) from exc

    def navigate_forward(self) -> None:
        try:
            self._driver.forward()
        except WebDriverException as exc:
            raise NavigationError(f"navigate_forward failed: {exc}", self._session_id) from exc

    # ------------------------------------------------------------------ #
    # Element interactions
    # ------------------------------------------------------------------ #

    def click(self, selector: str) -> None:
        """Click the element matching *selector* (CSS)."""
        logger.debug("[%s] click(%s)", self._session_id, selector)
        element = self._find(selector)
        try:
            self._retry(lambda: element.click())
        except WebDriverException as exc:
            raise ElementInteractionError(
                f"Cannot click {selector!r}: {exc}", self._session_id
            ) from exc

    def type_text(self, selector: str, text: str) -> None:
        """Clear the input and type *text* into *selector*."""
        logger.debug("[%s] type_text(%s, ...)", self._session_id, selector)
        element = self._find(selector)
        try:
            self._retry(lambda: (element.clear(), element.send_keys(text)))
        except WebDriverException as exc:
            raise ElementInteractionError(
                f"Cannot type into {selector!r}: {exc}", self._session_id
            ) from exc

    def get_text(self, selector: str) -> str:
        """Return inner text of the element matching *selector*."""
        element = self._find(selector)
        try:
            return element.text
        except WebDriverException as exc:
            raise ElementInteractionError(
                f"Cannot get text of {selector!r}: {exc}", self._session_id
            ) from exc

    def wait_for(self, selector: str, timeout: float) -> None:
        """Block until *selector* is visible or *timeout* seconds elapse."""
        logger.debug("[%s] wait_for(%s, %.1fs)", self._session_id, selector, timeout)
        try:
            WebDriverWait(self._driver, timeout).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, selector))
            )
        except SeleniumTimeoutException as exc:
            raise MCPTimeoutError(selector, timeout, self._session_id) from exc

    def wait_for_dom_stable(self, timeout: float = 5.0, poll: float = 0.3) -> None:
        """
        Smart DOM-stability wait.

        Polls `document.body.innerHTML.length` until two consecutive reads
        are identical, indicating the DOM has settled.
        """
        deadline = time.monotonic() + timeout
        prev_len: Optional[int] = None
        while time.monotonic() < deadline:
            cur_len = self._driver.execute_script("return document.body ? document.body.innerHTML.length : 0;")
            if cur_len == prev_len:
                return
            prev_len = cur_len
            time.sleep(poll)
        logger.warning("[%s] DOM did not stabilise within %.1fs", self._session_id, timeout)

    # ------------------------------------------------------------------ #
    # DOM / JS
    # ------------------------------------------------------------------ #

    def get_dom(self) -> str:
        """Return the full outer HTML of the current page."""
        return self._driver.page_source

    def execute_js(self, script: str, *args: Any) -> Any:
        """Execute *script* in the browser and return the result."""
        logger.debug("[%s] execute_js", self._session_id)
        try:
            return self._driver.execute_script(script, *args)
        except WebDriverException as exc:
            raise ScriptExecutionError(f"JS execution failed: {exc}", self._session_id) from exc

    # ------------------------------------------------------------------ #
    # Screenshot
    # ------------------------------------------------------------------ #

    def screenshot(self) -> str:
        """Return a base64-encoded PNG screenshot of the current viewport."""
        try:
            return self._driver.get_screenshot_as_base64()
        except WebDriverException as exc:
            raise ScreenshotError(f"Screenshot failed: {exc}", self._session_id) from exc

    def screenshot_on_error(self, label: str = "error") -> Optional[str]:
        """Take a best-effort screenshot; return base64 or None on failure."""
        if not self._settings.screenshot_on_error:
            return None
        try:
            import os
            from datetime import datetime

            directory = self._settings.screenshot_directory
            os.makedirs(directory, exist_ok=True)
            ts = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
            path = directory / f"{label}_{self._session_id[:8]}_{ts}.png"
            self._driver.save_screenshot(str(path))
            logger.info("[%s] Error screenshot saved: %s", self._session_id, path)
            return self._driver.get_screenshot_as_base64()
        except Exception:
            return None

    # ------------------------------------------------------------------ #
    # Logs
    # ------------------------------------------------------------------ #

    def get_console_logs(self) -> List[Dict[str, Any]]:
        """Return accumulated console log entries (BiDi + CDP fallback)."""
        # BiDi-collected logs take priority (populated by event listeners)
        if self._console_logs:
            return [log.to_dict() for log in self._console_logs]

        # CDP / classic performance log fallback for Chrome
        try:
            raw_logs = self._driver.get_log("browser")
            return [
                {
                    "level": entry.get("level", "").lower(),
                    "message": entry.get("message", ""),
                    "timestamp": entry.get("timestamp"),
                    "source": "cdp",
                }
                for entry in raw_logs
            ]
        except Exception:
            return []

    def get_network_logs(self) -> List[Dict[str, Any]]:
        """Return accumulated network request/response logs."""
        if self._network_logs:
            return [log.to_dict() for log in self._network_logs]

        # CDP performance log fallback for Chrome
        try:
            import json

            perf_logs = self._driver.get_log("performance")
            results = []
            for entry in perf_logs:
                msg = json.loads(entry.get("message", "{}"))
                method = msg.get("message", {}).get("method", "")
                if method in ("Network.requestWillBeSent", "Network.responseReceived"):
                    results.append({"cdp_method": method, "params": msg.get("message", {}).get("params", {})})
            return results
        except Exception:
            return []

    def get_performance_metrics(self) -> PerformanceMetrics:
        """Collect performance timing data via JavaScript."""
        try:
            timing: Dict[str, Any] = self._driver.execute_script(
                "return JSON.parse(JSON.stringify(window.performance.timing));"
            )
            nav_start = timing.get("navigationStart", 0)
            metrics = PerformanceMetrics(
                navigation_start=nav_start,
                dom_content_loaded=timing.get("domContentLoadedEventEnd", 0) - nav_start,
                dom_complete=timing.get("domComplete", 0) - nav_start,
                load_event_end=timing.get("loadEventEnd", 0) - nav_start,
                raw=timing,
            )
            # Try to get paint timings
            paint_entries: List[Dict] = self._driver.execute_script(
                "return performance.getEntriesByType('paint').map(e => ({name: e.name, startTime: e.startTime}));"
            ) or []
            for entry in paint_entries:
                if entry.get("name") == "first-paint":
                    metrics.first_paint = entry["startTime"]
                elif entry.get("name") == "first-contentful-paint":
                    metrics.first_contentful_paint = entry["startTime"]
            return metrics
        except Exception as exc:
            logger.warning("[%s] Could not collect performance metrics: %s", self._session_id, exc)
            return PerformanceMetrics()

    # ------------------------------------------------------------------ #
    # Interception
    # ------------------------------------------------------------------ #

    def add_intercept_pattern(self, pattern: str) -> None:
        """Register a URL pattern for network interception tracking."""
        if pattern not in self._intercept_patterns:
            self._intercept_patterns.append(pattern)
            logger.debug("[%s] Intercept pattern added: %s", self._session_id, pattern)

    def add_network_log(self, log: NetworkLog) -> None:
        """Append an externally captured network log entry (called by BiDi layer)."""
        self._network_logs.append(log)

    def add_console_log(self, log: ConsoleLog) -> None:
        """Append an externally captured console log entry (called by BiDi layer)."""
        self._console_logs.append(log)

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #

    def close(self) -> None:
        """Quit the WebDriver and mark the session as closed."""
        logger.info("[%s] Closing session", self._session_id)
        try:
            self._driver.quit()
        except Exception as exc:
            logger.warning("[%s] Error during driver quit: %s", self._session_id, exc)
        self._info.status = SessionStatus.CLOSED

    # ------------------------------------------------------------------ #
    # Private helpers
    # ------------------------------------------------------------------ #

    def _find(self, selector: str):
        """Locate an element by CSS selector; raise ElementNotFoundError if absent."""
        try:
            return self._driver.find_element(By.CSS_SELECTOR, selector)
        except NoSuchElementException as exc:
            raise ElementNotFoundError(selector, self._session_id) from exc

    def _retry(self, action, attempts: Optional[int] = None, backoff: Optional[float] = None):
        """Execute *action* with configurable retry on transient WebDriver errors."""
        max_attempts = attempts or self._settings.retry_max_attempts
        sleep = backoff or self._settings.retry_backoff
        last_exc: Optional[Exception] = None
        for attempt in range(1, max_attempts + 1):
            try:
                return action()
            except (StaleElementReferenceException, WebDriverException) as exc:
                last_exc = exc
                if attempt < max_attempts:
                    logger.debug("Retry %d/%d after: %s", attempt, max_attempts, exc)
                    time.sleep(sleep)
        raise last_exc  # type: ignore[misc]

    def _safe_current_url(self) -> Optional[str]:
        try:
            return self._driver.current_url
        except Exception:
            return None
