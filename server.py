"""
selenium-mcp – MCP server entrypoint.

Uses the official MCP Python SDK (FastMCP) to expose Selenium-powered
browser automation tools to any MCP-compatible client.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from config.logging_config import configure_logging, get_logger
from config.settings import settings
from driver.session_manager import SessionManager
from events.dispatcher import EventDispatcher
from tools.registry import ToolRegistry

# ──────────────────────────────────────────────────────────────────────────────
# Logging bootstrap
# ──────────────────────────────────────────────────────────────────────────────
configure_logging(level=settings.log_level, debug=settings.debug)
logger = get_logger("server")

# ──────────────────────────────────────────────────────────────────────────────
# Core objects
# ──────────────────────────────────────────────────────────────────────────────
dispatcher = EventDispatcher()
session_manager = SessionManager(settings, dispatcher)
registry = ToolRegistry(session_manager)

# ──────────────────────────────────────────────────────────────────────────────
# FastMCP server
# ──────────────────────────────────────────────────────────────────────────────
mcp = FastMCP(
    "mcp-selenium",
    instructions=(
        "Production-ready MCP server integrating Selenium 4 (BiDi) "
        "for browser automation. Supports Chrome and Firefox."
    ),
)


# ──────────────────────────────────────────────────────────────────────────────
# Helper: run synchronous tool call in a thread pool
# ──────────────────────────────────────────────────────────────────────────────
async def _run_tool(tool_name: str, arguments: dict[str, Any]) -> dict:
    """Execute a registered tool in a thread pool to avoid blocking."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None, registry.call, tool_name, arguments
    )


def _format_result(result: Any) -> str:
    """Format a tool result as a JSON string."""
    return json.dumps(result, ensure_ascii=False, default=str)


# ──────────────────────────────────────────────────────────────────────────────
# Session management tools
# ──────────────────────────────────────────────────────────────────────────────

@mcp.tool()
async def create_session(
    browser: str | None = None,
    headless: bool | None = None,
) -> str:
    """Create a new browser session. Defaults to Chrome headless."""
    result = await _run_tool("create_session", {
        k: v for k, v in {"browser": browser, "headless": headless}.items() if v is not None
    })
    return _format_result(result)


@mcp.tool()
async def close_session(session_id: str) -> str:
    """Close a browser session by ID."""
    result = await _run_tool("close_session", {"session_id": session_id})
    return _format_result(result)


@mcp.tool()
async def list_sessions() -> str:
    """List all active browser sessions."""
    result = await _run_tool("list_sessions", {})
    return _format_result(result)


@mcp.tool()
async def get_session_info(session_id: str | None = None) -> str:
    """Get metadata for a browser session."""
    result = await _run_tool("get_session_info", {
        k: v for k, v in {"session_id": session_id}.items() if v is not None
    })
    return _format_result(result)


# ──────────────────────────────────────────────────────────────────────────────
# Navigation tools
# ──────────────────────────────────────────────────────────────────────────────

@mcp.tool()
async def open_page(url: str, session_id: str | None = None) -> str:
    """Navigate the browser to a URL."""
    result = await _run_tool("open_page", {
        k: v for k, v in {"url": url, "session_id": session_id}.items() if v is not None
    })
    return _format_result(result)


@mcp.tool()
async def navigate_back(session_id: str | None = None) -> str:
    """Go back in browser history."""
    result = await _run_tool("navigate_back", {
        k: v for k, v in {"session_id": session_id}.items() if v is not None
    })
    return _format_result(result)


@mcp.tool()
async def navigate_forward(session_id: str | None = None) -> str:
    """Go forward in browser history."""
    result = await _run_tool("navigate_forward", {
        k: v for k, v in {"session_id": session_id}.items() if v is not None
    })
    return _format_result(result)


@mcp.tool()
async def get_dom(session_id: str | None = None) -> str:
    """Return the full page HTML source."""
    result = await _run_tool("get_dom", {
        k: v for k, v in {"session_id": session_id}.items() if v is not None
    })
    return _format_result(result)


# ──────────────────────────────────────────────────────────────────────────────
# Element interaction tools
# ──────────────────────────────────────────────────────────────────────────────

@mcp.tool()
async def click(selector: str, session_id: str | None = None) -> str:
    """Click a DOM element by CSS selector."""
    result = await _run_tool("click", {
        k: v for k, v in {"selector": selector, "session_id": session_id}.items() if v is not None
    })
    return _format_result(result)


@mcp.tool()
async def type_text(selector: str, text: str, session_id: str | None = None) -> str:
    """Clear an input and type text into it."""
    result = await _run_tool("type_text", {
        k: v for k, v in {"selector": selector, "text": text, "session_id": session_id}.items()
        if v is not None
    })
    return _format_result(result)


@mcp.tool()
async def get_text(selector: str, session_id: str | None = None) -> str:
    """Get the visible inner text of an element."""
    result = await _run_tool("get_text", {
        k: v for k, v in {"selector": selector, "session_id": session_id}.items() if v is not None
    })
    return _format_result(result)


@mcp.tool()
async def get_attribute(selector: str, attribute: str, session_id: str | None = None) -> str:
    """Get an attribute value from a DOM element (e.g. href, value, class)."""
    result = await _run_tool("get_attribute", {
        k: v for k, v in {
            "selector": selector, "attribute": attribute, "session_id": session_id,
        }.items() if v is not None
    })
    return _format_result(result)


@mcp.tool()
async def press_key(key: str, selector: str | None = None, session_id: str | None = None) -> str:
    """Press a keyboard key (e.g. Enter, Tab, Escape). Optionally target a specific element."""
    result = await _run_tool("press_key", {
        k: v for k, v in {
            "key": key, "selector": selector, "session_id": session_id,
        }.items() if v is not None
    })
    return _format_result(result)


@mcp.tool()
async def wait_for(
    selector: str, timeout: float = 10.0, session_id: str | None = None,
) -> str:
    """Wait until a CSS selector is visible on the page."""
    result = await _run_tool("wait_for", {
        k: v for k, v in {
            "selector": selector, "timeout": timeout, "session_id": session_id,
        }.items() if v is not None
    })
    return _format_result(result)


@mcp.tool()
async def wait_for_dom_stable(
    timeout: float = 5.0, session_id: str | None = None,
) -> str:
    """Wait until the DOM stops mutating (smart wait for AJAX content)."""
    result = await _run_tool("wait_for_dom_stable", {
        k: v for k, v in {"timeout": timeout, "session_id": session_id}.items() if v is not None
    })
    return _format_result(result)


# ──────────────────────────────────────────────────────────────────────────────
# Script & media tools
# ──────────────────────────────────────────────────────────────────────────────

@mcp.tool()
async def execute_js(script: str, session_id: str | None = None) -> str:
    """Execute JavaScript in the browser and return the result."""
    result = await _run_tool("execute_js", {
        k: v for k, v in {"script": script, "session_id": session_id}.items() if v is not None
    })
    return _format_result(result)


@mcp.tool()
async def screenshot(session_id: str | None = None) -> str:
    """Capture a base64-encoded PNG screenshot of the current viewport."""
    result = await _run_tool("screenshot", {
        k: v for k, v in {"session_id": session_id}.items() if v is not None
    })
    return _format_result(result)


# ──────────────────────────────────────────────────────────────────────────────
# Logs & network tools
# ──────────────────────────────────────────────────────────────────────────────

@mcp.tool()
async def get_console_logs(session_id: str | None = None) -> str:
    """Return all captured browser console log entries."""
    result = await _run_tool("get_console_logs", {
        k: v for k, v in {"session_id": session_id}.items() if v is not None
    })
    return _format_result(result)


@mcp.tool()
async def get_network_logs(session_id: str | None = None) -> str:
    """Return all captured network request/response entries."""
    result = await _run_tool("get_network_logs", {
        k: v for k, v in {"session_id": session_id}.items() if v is not None
    })
    return _format_result(result)


@mcp.tool()
async def get_performance_metrics(session_id: str | None = None) -> str:
    """Return page performance timing data."""
    result = await _run_tool("get_performance_metrics", {
        k: v for k, v in {"session_id": session_id}.items() if v is not None
    })
    return _format_result(result)


@mcp.tool()
async def intercept_requests(
    pattern: str, action: str = "log", session_id: str | None = None,
) -> str:
    """Register a URL pattern for network interception (log or block)."""
    result = await _run_tool("intercept_requests", {
        k: v for k, v in {
            "pattern": pattern, "action": action, "session_id": session_id,
        }.items() if v is not None
    })
    return _format_result(result)


# ──────────────────────────────────────────────────────────────────────────────
# Window / tab management
# ──────────────────────────────────────────────────────────────────────────────

@mcp.tool()
async def window(
    action: str,
    handle: str | None = None,
    index: int | None = None,
    session_id: str | None = None,
) -> str:
    """Manage browser windows and tabs. Actions: list, switch, switch_latest, close."""
    result = await _run_tool("window", {
        k: v for k, v in {
            "action": action, "handle": handle, "index": index, "session_id": session_id,
        }.items() if v is not None
    })
    return _format_result(result)


# ──────────────────────────────────────────────────────────────────────────────
# Frame / iFrame management
# ──────────────────────────────────────────────────────────────────────────────

@mcp.tool()
async def frame(
    action: str,
    identifier: str | int | None = None,
    session_id: str | None = None,
) -> str:
    """Switch focus to a frame or back to the main page. Actions: switch, default."""
    result = await _run_tool("frame", {
        k: v for k, v in {
            "action": action, "identifier": identifier, "session_id": session_id,
        }.items() if v is not None
    })
    return _format_result(result)


# ──────────────────────────────────────────────────────────────────────────────
# Alert / dialog handling
# ──────────────────────────────────────────────────────────────────────────────

@mcp.tool()
async def alert(
    action: str,
    text: str | None = None,
    session_id: str | None = None,
) -> str:
    """Handle browser alert/confirm/prompt dialogs. Actions: accept, dismiss, get_text, send_text."""  # noqa: E501
    result = await _run_tool("alert", {
        k: v for k, v in {
            "action": action, "text": text, "session_id": session_id,
        }.items() if v is not None
    })
    return _format_result(result)


# ──────────────────────────────────────────────────────────────────────────────
# Cookie management
# ──────────────────────────────────────────────────────────────────────────────

@mcp.tool()
async def add_cookie(
    name: str,
    value: str,
    domain: str | None = None,
    path: str | None = None,
    secure: bool | None = None,
    http_only: bool | None = None,
    session_id: str | None = None,
) -> str:
    """Add a cookie. Browser must be on a page from the cookie's domain."""
    result = await _run_tool("add_cookie", {
        k: v for k, v in {
            "name": name, "value": value, "domain": domain, "path": path,
            "secure": secure, "http_only": http_only, "session_id": session_id,
        }.items() if v is not None
    })
    return _format_result(result)


@mcp.tool()
async def get_cookies(name: str | None = None, session_id: str | None = None) -> str:
    """Get cookies. Returns all or a specific one by name."""
    result = await _run_tool("get_cookies", {
        k: v for k, v in {"name": name, "session_id": session_id}.items() if v is not None
    })
    return _format_result(result)


@mcp.tool()
async def delete_cookie(name: str | None = None, session_id: str | None = None) -> str:
    """Delete cookies. Deletes all or a specific one by name."""
    result = await _run_tool("delete_cookie", {
        k: v for k, v in {"name": name, "session_id": session_id}.items() if v is not None
    })
    return _format_result(result)


# ──────────────────────────────────────────────────────────────────────────────
# MCP Resources
# ──────────────────────────────────────────────────────────────────────────────

@mcp.resource(
    "accessibility://current",
    name="Current Page Accessibility Tree",
    description=(
        "A compact, structured JSON representation of interactive elements "
        "and text content on the current page. Much smaller than full HTML. "
        "Useful for understanding page layout and finding elements."
    ),
    mime_type="application/json",
)
async def accessibility_resource() -> str:
    """Return the accessibility tree of the current page."""
    try:
        loop = asyncio.get_running_loop()
        session = await loop.run_in_executor(None, session_manager.get_or_default)
        tree = await loop.run_in_executor(None, session.get_accessibility_tree)
        return json.dumps(tree, ensure_ascii=False, default=str)
    except Exception as exc:
        return json.dumps({"error": f"No active session: {exc}"})


@mcp.resource(
    "browser-status://current",
    name="Browser Session Status",
    description=(
        "Returns the current browser session status including "
        "URL, title, window count, and active session info."
    ),
    mime_type="text/plain",
)
async def browser_status_resource() -> str:
    """Return the current browser session status."""
    try:
        loop = asyncio.get_running_loop()
        session = await loop.run_in_executor(None, session_manager.get_or_default)
        info = session.info
        return (
            f"Session ID: {info.session_id}\n"
            f"Browser: {info.browser.value}\n"
            f"Status: {info.status.value}\n"
            f"URL: {info.current_url or 'N/A'}\n"
            f"Headless: {info.headless}"
        )
    except Exception:
        return "No active browser session"





# ──────────────────────────────────────────────────────────────────────────────
# Entrypoint
# ──────────────────────────────────────────────────────────────────────────────

def main() -> None:
    """Start the MCP server."""
    logger.info("selenium-mcp v1.0.0 starting via FastMCP (official SDK)")
    mcp.run()


if __name__ == "__main__":
    main()
