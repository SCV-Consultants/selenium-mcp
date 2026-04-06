"""JavaScript execution and screenshot MCP tools."""

from __future__ import annotations

import logging

from tools.base import BaseTool, with_error_screenshot

logger = logging.getLogger("selenium_mcp.tools.script")


class ScriptTools(BaseTool):
    """MCP tools for JS execution and screenshots."""

    @with_error_screenshot
    def execute_js(
        self,
        script: str,
        session_id: str | None = None,
    ) -> dict:
        """
        Execute arbitrary JavaScript inside the browser.

        Args:
            script:     JavaScript source to run (return value is captured).
            session_id: Session to target.

        Returns:
            dict with ``result`` key containing the script's return value.
        """
        session = self._get_session(session_id)
        result = session.execute_js(script)
        return {
            "success": True,
            "session_id": session.session_id,
            "result": result,
        }

    @with_error_screenshot
    def screenshot(self, session_id: str | None = None) -> dict:
        """
        Capture a viewport screenshot.

        Returns:
            dict with ``image_base64`` (PNG, base64-encoded) and ``mime_type``.
        """
        session = self._get_session(session_id)
        b64 = session.screenshot()
        return {
            "success": True,
            "session_id": session.session_id,
            "image_base64": b64,
            "mime_type": "image/png",
        }
