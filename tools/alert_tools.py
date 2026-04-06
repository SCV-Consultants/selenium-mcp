"""Alert/dialog handling MCP tools."""

from __future__ import annotations

import logging

from tools.base import BaseTool, with_error_screenshot

logger = logging.getLogger("selenium_mcp.tools.alert")


class AlertTools(BaseTool):
    """MCP tools for browser alert, confirm, and prompt dialogs."""

    @with_error_screenshot
    def alert(
        self,
        action: str,
        text: str | None = None,
        session_id: str | None = None,
    ) -> dict:
        """
        Handle browser alert/confirm/prompt dialogs.

        Args:
            action:     "accept", "dismiss", "get_text", or "send_text".
            text:       Text to send into a prompt (required for "send_text").
            session_id: Session to target.
        """
        session = self._get_session(session_id)

        if action == "accept":
            alert_text = session.alert_accept()
            return {
                "success": True,
                "session_id": session.session_id,
                "text": alert_text,
            }

        if action == "dismiss":
            alert_text = session.alert_dismiss()
            return {
                "success": True,
                "session_id": session.session_id,
                "text": alert_text,
            }

        if action == "get_text":
            alert_text = session.alert_get_text()
            return {
                "success": True,
                "session_id": session.session_id,
                "text": alert_text,
            }

        if action == "send_text":
            if text is None:
                return {
                    "success": False,
                    "error": "text is required for 'send_text' action",
                }
            session.alert_send_text(text)
            return {
                "success": True,
                "session_id": session.session_id,
            }

        return {
            "success": False,
            "error": f"Unknown alert action: {action!r}. Use: accept, dismiss, get_text, send_text",
        }
