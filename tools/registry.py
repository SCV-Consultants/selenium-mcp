"""Tool registry – aggregates all tool groups into a single callable map."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from driver.session_manager import SessionManager
from tools.interaction_tools import InteractionTools
from tools.log_tools import LogTools
from tools.navigation_tools import NavigationTools
from tools.script_tools import ScriptTools
from tools.session_tools import SessionTools


class ToolRegistry:
    """
    Aggregates all MCP tool implementations and exposes them by name.

    Usage::

        registry = ToolRegistry(session_manager)
        result = registry.call("open_page", {"url": "https://example.com"})
    """

    def __init__(self, session_manager: SessionManager) -> None:
        self._navigation = NavigationTools(session_manager)
        self._interaction = InteractionTools(session_manager)
        self._script = ScriptTools(session_manager)
        self._logs = LogTools(session_manager)
        self._session = SessionTools(session_manager)

        self._tools: dict[str, Callable[..., Any]] = {
            # Navigation
            "open_page": self._navigation.open_page,
            "navigate_back": self._navigation.navigate_back,
            "navigate_forward": self._navigation.navigate_forward,
            "get_dom": self._navigation.get_dom,
            # Interaction
            "click": self._interaction.click,
            "type_text": self._interaction.type_text,
            "get_text": self._interaction.get_text,
            "wait_for": self._interaction.wait_for,
            "wait_for_dom_stable": self._interaction.wait_for_dom_stable,
            # Script / media
            "execute_js": self._script.execute_js,
            "screenshot": self._script.screenshot,
            # Logs & network
            "get_console_logs": self._logs.get_console_logs,
            "get_network_logs": self._logs.get_network_logs,
            "get_performance_metrics": self._logs.get_performance_metrics,
            "intercept_requests": self._logs.intercept_requests,
            # Session management
            "create_session": self._session.create_session,
            "close_session": self._session.close_session,
            "list_sessions": self._session.list_sessions,
            "get_session_info": self._session.get_session_info,
        }

    def call(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """
        Invoke a registered tool by name.

        Args:
            tool_name:  Registered tool identifier.
            arguments:  Keyword arguments forwarded to the tool function.

        Raises:
            KeyError: If *tool_name* is not registered.
        """
        handler = self._tools[tool_name]
        return handler(**arguments)

    def list_tools(self) -> list[dict[str, Any]]:
        """Return MCP-formatted tool descriptors for all registered tools."""
        return [
            self._describe("open_page", "Navigate the browser to a URL",
                           {"url": "string"}, required=["url"]),
            self._describe("navigate_back", "Go back in browser history", {}),
            self._describe("navigate_forward", "Go forward in browser history", {}),
            self._describe("get_dom", "Return the full page HTML source",
                           {}),
            self._describe("click", "Click a DOM element by CSS selector",
                           {"selector": "string"}, required=["selector"]),
            self._describe("type_text",
                           "Clear an input and type text into it",
                           {"selector": "string", "text": "string"},
                           required=["selector", "text"]),
            self._describe("get_text",
                           "Get the visible inner text of an element",
                           {"selector": "string"}, required=["selector"]),
            self._describe("wait_for",
                           "Wait until a CSS selector is visible",
                           {"selector": "string", "timeout": "number"},
                           required=["selector"]),
            self._describe("wait_for_dom_stable",
                           "Wait until the DOM stops mutating (smart wait)",
                           {"timeout": "number"}),
            self._describe("execute_js",
                           "Execute JavaScript in the browser and return the result",
                           {"script": "string"}, required=["script"]),
            self._describe("screenshot",
                           "Capture a base64-encoded PNG screenshot",
                           {}),
            self._describe("get_console_logs",
                           "Return all captured browser console log entries",
                           {}),
            self._describe("get_network_logs",
                           "Return all captured network request/response entries",
                           {}),
            self._describe("get_performance_metrics",
                           "Return page performance timing data",
                           {}),
            self._describe("intercept_requests",
                           "Register a URL pattern for network interception",
                           {"pattern": "string", "action": "string"},
                           required=["pattern"]),
            self._describe("create_session",
                           "Create a new browser session",
                           {"browser": "string", "headless": "boolean"}),
            self._describe("close_session",
                           "Close a browser session by ID",
                           {"session_id": "string"}, required=["session_id"]),
            self._describe("list_sessions",
                           "List all active browser sessions",
                           {}),
            self._describe("get_session_info",
                           "Get metadata for a session",
                           {}),
        ]

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _describe(
        name: str,
        description: str,
        params: dict[str, str],
        required: list[str] | None = None,
    ) -> dict[str, Any]:
        """Build a minimal MCP tool descriptor."""
        properties: dict[str, Any] = {}
        for param_name, param_type in params.items():
            entry: dict[str, Any] = {}
            if param_type == "string":
                entry["type"] = "string"
            elif param_type == "number":
                entry["type"] = "number"
            elif param_type == "boolean":
                entry["type"] = "boolean"
            else:
                entry["type"] = param_type
            properties[param_name] = entry

        # Always add optional session_id
        properties["session_id"] = {"type": "string", "description": "Session ID (optional)"}

        schema: dict[str, Any] = {"type": "object", "properties": properties}
        if required:
            schema["required"] = required

        return {
            "name": name,
            "description": description,
            "inputSchema": schema,
        }
