"""Session manager – tracks all active BrowserSession instances."""

from __future__ import annotations

import logging

from config.settings import Settings
from driver.factory import build_driver
from driver.session import BrowserSession
from models.exceptions import SessionLimitError, SessionNotFoundError
from models.session import BrowserType

logger = logging.getLogger("selenium_mcp.driver.session_manager")


class SessionManager:
    """
    Central registry for all active browser sessions.

    Thread-safety note: all public methods are synchronous; the MCP server
    must serialize calls that mutate the registry (e.g. via asyncio.Lock).
    """

    def __init__(self, settings: Settings, dispatcher) -> None:
        self._settings = settings
        self._dispatcher = dispatcher
        self._sessions: dict[str, BrowserSession] = {}

    # ------------------------------------------------------------------ #
    # CRUD
    # ------------------------------------------------------------------ #

    def create_session(
        self,
        browser: str | None = None,
        headless: bool | None = None,
    ) -> BrowserSession:
        """
        Create a new browser session.

        Args:
            browser: "chrome" | "firefox" (defaults to settings.default_browser)
            headless: Override the global headless flag.

        Returns:
            A ready BrowserSession.

        Raises:
            SessionLimitError: If max_sessions is already reached.
        """
        if len(self._sessions) >= self._settings.max_sessions:
            raise SessionLimitError(
                f"Max sessions reached ({self._settings.max_sessions}). "
                "Close an existing session before creating a new one."
            )

        browser_type = BrowserType(browser or self._settings.default_browser)
        driver = build_driver(browser_type, self._settings, headless)

        session = BrowserSession(
            driver=driver,
            browser=browser_type,
            settings=self._settings,
            dispatcher=self._dispatcher,
            headless=headless if headless is not None else self._settings.headless,
        )

        self._sessions[session.session_id] = session
        logger.info("Session created: %s (%s)", session.session_id, browser_type.value)
        return session

    def get_session(self, session_id: str) -> BrowserSession:
        """Return the session with *session_id* or raise SessionNotFoundError."""
        session = self._sessions.get(session_id)
        if session is None:
            raise SessionNotFoundError(f"Session not found: {session_id!r}")
        return session

    def get_or_default(self, session_id: str | None = None) -> BrowserSession:
        """
        Return the session identified by *session_id*.

        If *session_id* is None and exactly one session exists, return it.
        If no sessions exist, create one automatically.
        """
        if session_id:
            return self.get_session(session_id)

        if not self._sessions:
            logger.info("No active session – auto-creating one.")
            return self.create_session()

        if len(self._sessions) == 1:
            return next(iter(self._sessions.values()))

        raise SessionNotFoundError(
            "Multiple sessions are active. Provide an explicit session_id."
        )

    def close_session(self, session_id: str) -> None:
        """Close and remove a session."""
        session = self.get_session(session_id)
        session.close()
        del self._sessions[session_id]
        logger.info("Session removed: %s", session_id)

    def close_all(self) -> None:
        """Close every active session (called on server shutdown)."""
        for sid in list(self._sessions):
            try:
                self._sessions[sid].close()
            except Exception as exc:
                logger.warning("Error closing session %s: %s", sid, exc)
        self._sessions.clear()
        logger.info("All sessions closed.")

    def list_sessions(self) -> list:
        """Return a serialisable list of session metadata."""
        return [s.info.to_dict() for s in self._sessions.values()]

    def __len__(self) -> int:
        return len(self._sessions)
