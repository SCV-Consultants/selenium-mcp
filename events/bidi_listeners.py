"""
BiDi event listeners.

Attaches Selenium 4 BiDi (WebSocket) listeners to an active WebDriver session
and routes incoming events through the EventDispatcher.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from models.events import BrowserEvent, ConsoleLogEvent
from models.network import ConsoleLog

if TYPE_CHECKING:
    from driver.session import BrowserSession
    from events.dispatcher import EventDispatcher

logger = logging.getLogger("selenium_mcp.events.bidi_listeners")


class BiDiListenerManager:
    """
    Manages BiDi event subscriptions for a single BrowserSession.

    Each public ``attach_*`` method registers a listener directly with
    Selenium's BiDi WebSocket connection.  When the browser emits an event,
    the listener:

    1. Builds a typed BrowserEvent model.
    2. Appends raw data to the session's in-memory log stores.
    3. Publishes the event through the EventDispatcher for any downstream consumers.
    """

    def __init__(
        self,
        session: BrowserSession,
        dispatcher: EventDispatcher,
        loop: asyncio.AbstractEventLoop | None = None,
    ) -> None:
        self._session = session
        self._dispatcher = dispatcher
        self._loop = loop
        self._attached: list[str] = []

    # ------------------------------------------------------------------ #
    # Public attach methods
    # ------------------------------------------------------------------ #

    def attach_console_listener(self) -> None:
        """Subscribe to browser console log events via BiDi."""
        try:
            driver = self._session.driver
            # Selenium 4 BiDi – script.Message / Log.EntryAdded
            driver.script.add_console_message_handler(self._on_console_message)
            self._attached.append("console")
            logger.debug("[%s] BiDi console listener attached", self._session.session_id)
        except Exception as exc:
            logger.warning(
                "[%s] Could not attach BiDi console listener: %s (BiDi may not be supported)",
                self._session.session_id,
                exc,
            )

    def attach_network_listener(self) -> None:
        """Subscribe to network request/response events via BiDi."""
        try:
            driver = self._session.driver
            driver.script.add_javascript_error_handler(self._on_js_error)
            self._attached.append("js_error")
            logger.debug("[%s] BiDi JS-error listener attached", self._session.session_id)
        except Exception as exc:
            logger.warning(
                "[%s] Could not attach BiDi JS-error listener: %s",
                self._session.session_id,
                exc,
            )

        # CDP-based network interception (Chrome)
        try:
            driver = self._session.driver
            driver.execute_cdp_cmd("Network.enable", {})
            logger.debug("[%s] CDP Network.enable called", self._session.session_id)
            self._attached.append("cdp_network")
        except Exception as exc:
            logger.debug(
                "[%s] CDP network interception not available: %s",
                self._session.session_id,
                exc,
            )

    def detach_all(self) -> None:
        """Remove all registered listeners (best effort)."""
        for name in self._attached:
            try:
                if name == "console":
                    self._session.driver.script.remove_console_message_handler(
                        self._on_console_message
                    )
                elif name == "js_error":
                    self._session.driver.script.remove_javascript_error_handler(
                        self._on_js_error
                    )
            except Exception as exc:
                logger.debug("Error detaching %s listener: %s", name, exc)
        self._attached.clear()
        logger.debug("[%s] BiDi listeners detached", self._session.session_id)

    # ------------------------------------------------------------------ #
    # Raw BiDi callbacks (called by Selenium on the WebDriver thread)
    # ------------------------------------------------------------------ #

    def _on_console_message(self, msg: Any) -> None:
        """Handle a BiDi console.log-style message."""
        try:
            # Selenium 4.x wraps BiDi script messages in a ConsoleMessageInfo object
            level = getattr(msg, "level", "log")
            if hasattr(level, "value"):
                level = level.value  # Enum → str
            text = getattr(msg, "text", str(msg))

            console_log = ConsoleLog(
                level=str(level).lower(),
                message=str(text),
                source="bidi",
            )
            self._session.add_console_log(console_log)

            event = ConsoleLogEvent(
                session_id=self._session.session_id,
                level=console_log.level,
                message=console_log.message,
                source="bidi",
            )
            self._publish(event)
            logger.debug("[%s] console.%s: %s", self._session.session_id, level, text)
        except Exception as exc:
            logger.warning("Error processing console message: %s", exc)

    def _on_js_error(self, error: Any) -> None:
        """Handle a BiDi JavaScript error event."""
        try:
            message = getattr(error, "text", str(error))
            console_log = ConsoleLog(level="error", message=str(message), source="bidi-js-error")
            self._session.add_console_log(console_log)

            event = ConsoleLogEvent(
                session_id=self._session.session_id,
                level="error",
                message=str(message),
                source="bidi-js-error",
            )
            self._publish(event)
        except Exception as exc:
            logger.warning("Error processing JS error event: %s", exc)

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def _publish(self, event: BrowserEvent) -> None:
        """Publish to the dispatcher from the Selenium callback thread."""
        try:
            self._dispatcher.publish_sync(event, self._loop)
        except Exception as exc:
            logger.debug("Dispatcher publish error: %s", exc)
