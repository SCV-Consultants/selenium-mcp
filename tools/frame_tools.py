"""Frame/iFrame management MCP tools."""

from __future__ import annotations

import logging

from tools.base import BaseTool, with_error_screenshot

logger = logging.getLogger("selenium_mcp.tools.frame")


class FrameTools(BaseTool):
    """MCP tools for frame/iFrame management."""

    @with_error_screenshot
    def frame(
        self,
        action: str,
        identifier: str | int | None = None,
        session_id: str | None = None,
    ) -> dict:
        """
        Manage frame focus.

        Args:
            action:     "switch" to enter a frame, "default" to return to main page.
            identifier: Frame name, ID (string) or index (int) for "switch" action.
            session_id: Session to target.
        """
        session = self._get_session(session_id)

        if action == "switch":
            if identifier is None:
                return {
                    "success": False,
                    "error": "identifier is required for 'switch' action",
                }
            session.switch_frame(identifier)
            return {
                "success": True,
                "session_id": session.session_id,
                "frame": str(identifier),
            }

        if action == "default":
            session.switch_to_default_content()
            return {
                "success": True,
                "session_id": session.session_id,
                "frame": "default",
            }

        return {
            "success": False,
            "error": f"Unknown frame action: {action!r}. Use: switch, default",
        }
