"""Log collection and network interception MCP tools."""

from __future__ import annotations

import logging

from events.network_interceptor import NetworkInterceptor
from tools.base import BaseTool

logger = logging.getLogger("selenium_mcp.tools.log")


class LogTools(BaseTool):
    """MCP tools for log retrieval and network interception."""

    def get_console_logs(self, session_id: str | None = None) -> dict:
        """
        Return all console log entries captured for the session.

        Entries are collected via BiDi listeners (preferred) or CDP fallback.

        Returns:
            dict with ``logs`` list.
        """
        session = self._get_session(session_id)
        logs = session.get_console_logs()
        return {
            "success": True,
            "session_id": session.session_id,
            "count": len(logs),
            "logs": logs,
        }

    def get_network_logs(self, session_id: str | None = None) -> dict:
        """
        Return all network request/response log entries for the session.

        Returns:
            dict with ``logs`` list.
        """
        session = self._get_session(session_id)
        logs = session.get_network_logs()
        return {
            "success": True,
            "session_id": session.session_id,
            "count": len(logs),
            "logs": logs,
        }

    def get_performance_metrics(self, session_id: str | None = None) -> dict:
        """
        Return browser performance timing data for the current page.

        Returns:
            dict with timing fields in milliseconds (relative to navigation start).
        """
        session = self._get_session(session_id)
        metrics = session.get_performance_metrics()
        return {
            "success": True,
            "session_id": session.session_id,
            "metrics": metrics.to_dict(),
        }

    def intercept_requests(
        self,
        pattern: str,
        action: str = "log",
        session_id: str | None = None,
    ) -> dict:
        """
        Register a URL interception rule for the session.

        Args:
            pattern:    Glob-style URL pattern (e.g. ``"*api/v1/*"``).
            action:     ``"log"`` (default) or ``"block"``.
            session_id: Session to target.

        Returns:
            dict confirming rule registration.
        """
        session = self._get_session(session_id)
        interceptor = NetworkInterceptor(session)
        rule = interceptor.add_rule(pattern, action)
        return {
            "success": True,
            "session_id": session.session_id,
            "rule": rule.to_dict(),
        }
