"""Navigation and page-level MCP tools."""

from __future__ import annotations

import logging
from typing import Optional

from tools.base import BaseTool, with_error_screenshot

logger = logging.getLogger("selenium_mcp.tools.navigation")


class NavigationTools(BaseTool):
    """MCP tools for browser navigation actions."""

    @with_error_screenshot
    def open_page(self, url: str, session_id: Optional[str] = None) -> dict:
        """
        Navigate to *url* in the active browser session.

        Args:
            url:        Target URL (must include scheme, e.g. ``https://``).
            session_id: Session to use; auto-selected if only one exists.

        Returns:
            dict with ``session_id`` and ``current_url``.
        """
        session = self._get_session(session_id)
        session.open_page(url)
        return {
            "success": True,
            "session_id": session.session_id,
            "current_url": session.info.current_url,
        }

    @with_error_screenshot
    def navigate_back(self, session_id: Optional[str] = None) -> dict:
        """Navigate back in browser history."""
        session = self._get_session(session_id)
        session.navigate_back()
        return {"success": True, "session_id": session.session_id}

    @with_error_screenshot
    def navigate_forward(self, session_id: Optional[str] = None) -> dict:
        """Navigate forward in browser history."""
        session = self._get_session(session_id)
        session.navigate_forward()
        return {"success": True, "session_id": session.session_id}

    def get_dom(self, session_id: Optional[str] = None) -> dict:
        """
        Return the full outer HTML of the current page.

        Returns:
            dict with ``html`` key.
        """
        session = self._get_session(session_id)
        html = session.get_dom()
        return {
            "success": True,
            "session_id": session.session_id,
            "html": html,
            "length": len(html),
        }
