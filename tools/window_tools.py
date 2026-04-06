"""Window and tab management MCP tools."""

from __future__ import annotations

import logging

from tools.base import BaseTool, with_error_screenshot

logger = logging.getLogger("selenium_mcp.tools.window")


class WindowTools(BaseTool):
    """MCP tools for browser window/tab management."""

    @with_error_screenshot
    def window(
        self,
        action: str,
        handle: str | None = None,
        index: int | None = None,
        session_id: str | None = None,
    ) -> dict:
        """
        Manage browser windows and tabs.

        Args:
            action:     One of "list", "switch", "switch_latest", "close".
            handle:     Window handle to switch to (for "switch" action).
            index:      Window index to switch to (for "switch" action).
            session_id: Session to target.
        """
        session = self._get_session(session_id)

        if action == "list":
            windows = session.list_windows()
            return {
                "success": True,
                "session_id": session.session_id,
                "count": len(windows),
                "windows": windows,
            }

        if action == "switch":
            new_handle = session.switch_window(handle=handle, index=index)
            return {
                "success": True,
                "session_id": session.session_id,
                "handle": new_handle,
            }

        if action == "switch_latest":
            new_handle = session.switch_window()  # defaults to last
            return {
                "success": True,
                "session_id": session.session_id,
                "handle": new_handle,
            }

        if action == "close":
            new_handle = session.close_window()
            return {
                "success": True,
                "session_id": session.session_id,
                "handle": new_handle,
            }

        return {
            "success": False,
            "error": f"Unknown window action: {action!r}. Use: list, switch, switch_latest, close",
        }
