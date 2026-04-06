"""Browser session wrapper – owns a single WebDriver instance."""

from __future__ import annotations

import logging
import time
import uuid
from datetime import UTC
from typing import TYPE_CHECKING, Any

from selenium.common.exceptions import (
    NoAlertPresentException,
    NoSuchElementException,
    NoSuchFrameException,
    NoSuchWindowException,
    StaleElementReferenceException,
    WebDriverException,
)
from selenium.common.exceptions import (
    TimeoutException as SeleniumTimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from config.settings import Settings
from models.exceptions import (
    AlertError,
    CookieError,
    ElementInteractionError,
    ElementNotFoundError,
    FrameError,
    NavigationError,
    ScreenshotError,
    ScriptExecutionError,
    WindowError,
)
from models.exceptions import (
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
        dispatcher: EventDispatcher,
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

        self._network_logs: list[NetworkLog] = []
        self._console_logs: list[ConsoleLog] = []
        self._intercept_patterns: list[str] = []

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

    def get_attribute(self, selector: str, attribute: str) -> str | None:
        """Return the value of *attribute* on the element matching *selector*."""
        element = self._find(selector)
        try:
            return element.get_attribute(attribute)
        except WebDriverException as exc:
            raise ElementInteractionError(
                f"Cannot get attribute {attribute!r} of {selector!r}: {exc}",
                self._session_id,
            ) from exc

    def press_key(self, key: str, selector: str | None = None) -> None:
        """
        Press a keyboard key.

        If *selector* is given, sends the key to that element;
        otherwise sends it to the active element.
        """
        # Map common key names to Selenium Keys constants
        key_map = {
            "enter": Keys.ENTER,
            "return": Keys.RETURN,
            "tab": Keys.TAB,
            "escape": Keys.ESCAPE,
            "esc": Keys.ESCAPE,
            "backspace": Keys.BACKSPACE,
            "delete": Keys.DELETE,
            "space": Keys.SPACE,
            "arrowup": Keys.ARROW_UP,
            "arrowdown": Keys.ARROW_DOWN,
            "arrowleft": Keys.ARROW_LEFT,
            "arrowright": Keys.ARROW_RIGHT,
            "home": Keys.HOME,
            "end": Keys.END,
            "pageup": Keys.PAGE_UP,
            "pagedown": Keys.PAGE_DOWN,
            "f1": Keys.F1, "f2": Keys.F2, "f3": Keys.F3, "f4": Keys.F4,
            "f5": Keys.F5, "f6": Keys.F6, "f7": Keys.F7, "f8": Keys.F8,
            "f9": Keys.F9, "f10": Keys.F10, "f11": Keys.F11, "f12": Keys.F12,
            "control": Keys.CONTROL, "ctrl": Keys.CONTROL,
            "shift": Keys.SHIFT, "alt": Keys.ALT, "meta": Keys.META,
        }
        resolved = key_map.get(key.lower(), key)
        try:
            if selector:
                element = self._find(selector)
                element.send_keys(resolved)
            else:
                from selenium.webdriver.common.action_chains import ActionChains
                ActionChains(self._driver).send_keys(resolved).perform()
        except WebDriverException as exc:
            raise ElementInteractionError(
                f"Cannot press key {key!r}: {exc}", self._session_id
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
        prev_len: int | None = None
        while time.monotonic() < deadline:
            js = (
                "return document.body"
                " ? document.body.innerHTML.length : 0;"
            )
            cur_len = self._driver.execute_script(js)
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

    def screenshot_on_error(self, label: str = "error") -> str | None:
        """Take a best-effort screenshot; return base64 or None on failure."""
        if not self._settings.screenshot_on_error:
            return None
        try:
            import os
            from datetime import datetime

            directory = self._settings.screenshot_directory
            os.makedirs(directory, exist_ok=True)
            ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
            path = directory / f"{label}_{self._session_id[:8]}_{ts}.png"
            self._driver.save_screenshot(str(path))
            logger.info("[%s] Error screenshot saved: %s", self._session_id, path)
            return self._driver.get_screenshot_as_base64()
        except Exception:
            return None

    # ------------------------------------------------------------------ #
    # Logs
    # ------------------------------------------------------------------ #

    def get_console_logs(self) -> list[dict[str, Any]]:
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

    def get_network_logs(self) -> list[dict[str, Any]]:
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
                    params = msg.get("message", {}).get("params", {})
                    results.append(
                        {"cdp_method": method, "params": params}
                    )
            return results
        except Exception:
            return []

    def get_performance_metrics(self) -> PerformanceMetrics:
        """Collect performance timing data via JavaScript."""
        try:
            timing: dict[str, Any] = self._driver.execute_script(
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
            paint_entries: list[dict] = self._driver.execute_script(
                "return performance.getEntriesByType('paint')"
                ".map(e => ({name: e.name, startTime: e.startTime}));"
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
    # Window / Tab management
    # ------------------------------------------------------------------ #

    def list_windows(self) -> list[dict[str, str]]:
        """Return all window handles with the current handle marked."""
        try:
            handles = self._driver.window_handles
            current = self._driver.current_window_handle
            return [
                {"handle": h, "active": h == current}
                for h in handles
            ]
        except WebDriverException as exc:
            raise WindowError(f"Cannot list windows: {exc}", self._session_id) from exc

    def switch_window(self, handle: str | None = None, index: int | None = None) -> str:
        """
        Switch to a window by handle or index.

        Returns the new window handle.
        """
        try:
            if handle:
                self._driver.switch_to.window(handle)
            elif index is not None:
                handles = self._driver.window_handles
                if index < 0 or index >= len(handles):
                    raise WindowError(
                        f"Window index {index} out of range (0-{len(handles)-1})",
                        self._session_id,
                    )
                self._driver.switch_to.window(handles[index])
            else:
                # Switch to the latest (last) window
                handles = self._driver.window_handles
                self._driver.switch_to.window(handles[-1])
            return self._driver.current_window_handle
        except NoSuchWindowException as exc:
            raise WindowError(f"Window not found: {exc}", self._session_id) from exc
        except WebDriverException as exc:
            raise WindowError(f"Cannot switch window: {exc}", self._session_id) from exc

    def close_window(self) -> str | None:
        """Close current window/tab and switch to previous. Returns new handle or None."""
        try:
            self._driver.close()
            handles = self._driver.window_handles
            if handles:
                self._driver.switch_to.window(handles[-1])
                return self._driver.current_window_handle
            return None
        except WebDriverException as exc:
            raise WindowError(f"Cannot close window: {exc}", self._session_id) from exc

    # ------------------------------------------------------------------ #
    # Frame / iFrame management
    # ------------------------------------------------------------------ #

    def switch_frame(self, identifier: str | int) -> None:
        """
        Switch to a frame by name, ID (string) or index (int).
        """
        try:
            self._driver.switch_to.frame(identifier)
        except NoSuchFrameException as exc:
            raise FrameError(
                f"Frame not found: {identifier!r}", self._session_id
            ) from exc
        except WebDriverException as exc:
            raise FrameError(f"Cannot switch frame: {exc}", self._session_id) from exc

    def switch_to_default_content(self) -> None:
        """Switch back to the main/top-level page from any frame."""
        try:
            self._driver.switch_to.default_content()
        except WebDriverException as exc:
            raise FrameError(
                f"Cannot switch to default content: {exc}", self._session_id
            ) from exc

    # ------------------------------------------------------------------ #
    # Alert / Dialog handling
    # ------------------------------------------------------------------ #

    def alert_accept(self) -> str:
        """Accept (OK) the active alert. Returns the alert text."""
        try:
            alert = self._driver.switch_to.alert
            text = alert.text
            alert.accept()
            return text
        except NoAlertPresentException as exc:
            raise AlertError("No alert present", self._session_id) from exc
        except WebDriverException as exc:
            raise AlertError(f"Cannot accept alert: {exc}", self._session_id) from exc

    def alert_dismiss(self) -> str:
        """Dismiss (Cancel) the active alert. Returns the alert text."""
        try:
            alert = self._driver.switch_to.alert
            text = alert.text
            alert.dismiss()
            return text
        except NoAlertPresentException as exc:
            raise AlertError("No alert present", self._session_id) from exc
        except WebDriverException as exc:
            raise AlertError(f"Cannot dismiss alert: {exc}", self._session_id) from exc

    def alert_get_text(self) -> str:
        """Get the text of the active alert without dismissing it."""
        try:
            return self._driver.switch_to.alert.text
        except NoAlertPresentException as exc:
            raise AlertError("No alert present", self._session_id) from exc

    def alert_send_text(self, text: str) -> None:
        """Type text into a prompt dialog."""
        try:
            alert = self._driver.switch_to.alert
            alert.send_keys(text)
        except NoAlertPresentException as exc:
            raise AlertError("No alert present", self._session_id) from exc
        except WebDriverException as exc:
            raise AlertError(f"Cannot send text to alert: {exc}", self._session_id) from exc

    # ------------------------------------------------------------------ #
    # Cookie management
    # ------------------------------------------------------------------ #

    def add_cookie(self, name: str, value: str, **kwargs) -> None:
        """Add a cookie. Browser must be on a page from the cookie's domain."""
        cookie: dict[str, Any] = {"name": name, "value": value}
        cookie.update(kwargs)
        try:
            self._driver.add_cookie(cookie)
        except WebDriverException as exc:
            raise CookieError(
                f"Cannot add cookie {name!r}: {exc}", self._session_id
            ) from exc

    def get_cookies(self, name: str | None = None) -> list[dict[str, Any]]:
        """Get all cookies, or a specific one by *name*."""
        try:
            if name:
                cookie = self._driver.get_cookie(name)
                return [cookie] if cookie else []
            return self._driver.get_cookies()
        except WebDriverException as exc:
            raise CookieError(f"Cannot get cookies: {exc}", self._session_id) from exc

    def delete_cookies(self, name: str | None = None) -> None:
        """Delete a specific cookie by *name*, or all cookies."""
        try:
            if name:
                self._driver.delete_cookie(name)
            else:
                self._driver.delete_all_cookies()
        except WebDriverException as exc:
            raise CookieError(
                f"Cannot delete cookie(s): {exc}", self._session_id
            ) from exc

    # ------------------------------------------------------------------ #
    # Accessibility
    # ------------------------------------------------------------------ #

    def get_accessibility_tree(self) -> dict[str, Any]:
        """
        Return a compact accessibility tree of the current page.

        Uses JavaScript to walk the DOM and extract interactive elements,
        landmarks, headings, and text content — much smaller than full HTML
        and far more useful for LLMs.
        """
        script = """
        function buildTree(node, depth) {
            if (depth > 15) return null;
            var result = {};
            var tag = node.tagName ? node.tagName.toLowerCase() : '';
            var role = node.getAttribute ? (node.getAttribute('role') || '') : '';
            var ariaLabel = node.getAttribute ? (node.getAttribute('aria-label') || '') : '';
            var interactiveTags = ['a','button','input','select','textarea','details','summary'];
            var isInteractive = interactiveTags.indexOf(tag) !== -1 || role;
            var id = node.id || '';
            var text = '';

            if (node.nodeType === 3) {
                text = node.textContent.trim();
                if (!text) return null;
                return {type: 'text', content: text.substring(0, 200)};
            }
            if (node.nodeType !== 1) return null;

            result.tag = tag;
            if (id) result.id = id;
            if (role) result.role = role;
            if (ariaLabel) result.ariaLabel = ariaLabel;
            if (tag === 'a') result.href = node.getAttribute('href') || '';
            if (tag === 'input') {
                result.type = node.getAttribute('type') || 'text';
                result.name = node.getAttribute('name') || '';
                result.value = node.value || '';
            }
            if (tag === 'img') result.alt = node.getAttribute('alt') || '';

            var children = [];
            for (var i = 0; i < node.childNodes.length; i++) {
                var child = buildTree(node.childNodes[i], depth + 1);
                if (child) children.push(child);
            }

            if (!isInteractive && !id && children.length === 0) return null;
            if (!isInteractive && !id && children.length === 1 && children[0].type === 'text') {
                return children[0];
            }

            if (children.length > 0) result.children = children;
            return result;
        }
        return {
            url: document.location.href,
            title: document.title,
            tree: buildTree(document.body, 0)
        };
        """
        try:
            return self._driver.execute_script(script)
        except WebDriverException:
            return {"url": self._safe_current_url(), "title": "", "tree": None}

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

    def _retry(self, action, attempts: int | None = None, backoff: float | None = None):
        """Execute *action* with configurable retry on transient WebDriver errors."""
        max_attempts = attempts or self._settings.retry_max_attempts
        sleep = backoff or self._settings.retry_backoff
        last_exc: Exception | None = None
        for attempt in range(1, max_attempts + 1):
            try:
                return action()
            except (StaleElementReferenceException, WebDriverException) as exc:
                last_exc = exc
                if attempt < max_attempts:
                    logger.debug("Retry %d/%d after: %s", attempt, max_attempts, exc)
                    time.sleep(sleep)
        raise last_exc  # type: ignore[misc]

    def _safe_current_url(self) -> str | None:
        try:
            return self._driver.current_url
        except Exception:
            return None
