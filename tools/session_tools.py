"""Session management MCP tools."""

from __future__ import annotations

import logging

from tools.base import BaseTool

logger = logging.getLogger("selenium_mcp.tools.session")


class SessionTools(BaseTool):
    """MCP tools for browser session lifecycle management."""

    def create_session(
        self,
        browser: str | None = None,
        headless: bool | None = None,
    ) -> dict:
        """
        Create a new browser session.

        Args:
            browser:  ``"chrome"`` or ``"firefox"`` (uses server default if omitted).
            headless: Override the global headless flag.

        Returns:
            dict with ``session_id`` and session metadata.
        """
        session = self._session_manager.create_session(browser=browser, headless=headless)
        return {
            "success": True,
            "session": session.info.to_dict(),
        }

    def close_session(self, session_id: str) -> dict:
        """
        Close and destroy a browser session.

        Args:
            session_id: ID of the session to close.
        """
        self._session_manager.close_session(session_id)
        return {"success": True, "session_id": session_id, "status": "closed"}

    def list_sessions(self) -> dict:
        """
        List all active browser sessions.

        Returns:
            dict with ``sessions`` list.
        """
        sessions = self._session_manager.list_sessions()
        return {
            "success": True,
            "count": len(sessions),
            "sessions": sessions,
        }

    def get_session_info(self, session_id: str | None = None) -> dict:
        """
        Return metadata for the specified (or default) session.

        Args:
            session_id: Session to query; auto-selected if only one exists.
        """
        session = self._get_session(session_id)
        return {
            "success": True,
            "session": session.info.to_dict(),
        }
