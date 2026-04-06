"""
selenium-mcp – MCP server entrypoint.

Implements the Model Context Protocol (MCP) over stdio (JSON-RPC 2.0),
exposing Selenium-powered browser automation tools to any MCP-compatible client.

Protocol flow:
    client → initialize        → server responds with capabilities
    client → tools/list        → server returns tool descriptors
    client → tools/call        → server executes tool, returns result
    client → notifications/... → server acknowledges (no-op for now)
"""

from __future__ import annotations

import asyncio
import json
import sys
from typing import Any

from config.logging_config import configure_logging, get_logger
from config.settings import settings
from driver.session_manager import SessionManager
from events.dispatcher import EventDispatcher
from models.exceptions import SeleniumMCPError
from tools.registry import ToolRegistry

# ──────────────────────────────────────────────────────────────────────────────
# Logging bootstrap (before any other imports that may log)
# ──────────────────────────────────────────────────────────────────────────────
configure_logging(level=settings.log_level, debug=settings.debug)
logger = get_logger("server")

# ──────────────────────────────────────────────────────────────────────────────
# MCP protocol constants
# ──────────────────────────────────────────────────────────────────────────────
PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "selenium-mcp"
SERVER_VERSION = "1.0.0"


# ──────────────────────────────────────────────────────────────────────────────
# JSON-RPC helpers
# ──────────────────────────────────────────────────────────────────────────────

def _ok(request_id: Any, result: Any) -> dict:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _err(request_id: Any, code: int, message: str, data: Any = None) -> dict:
    error: dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    return {"jsonrpc": "2.0", "id": request_id, "error": error}


def _send(obj: dict) -> None:
    """Write a JSON-RPC message to stdout followed by a newline."""
    line = json.dumps(obj, ensure_ascii=False)
    sys.stdout.write(line + "\n")
    sys.stdout.flush()


# ──────────────────────────────────────────────────────────────────────────────
# MCP Server
# ──────────────────────────────────────────────────────────────────────────────

class MCPServer:
    """
    Async MCP server that reads JSON-RPC messages from stdin and writes
    responses to stdout.

    Architecture:
    - ``EventDispatcher``  – async pub/sub hub for BiDi browser events
    - ``SessionManager``   – owns all active WebDriver sessions
    - ``ToolRegistry``     – maps tool names → callable implementations
    """

    def __init__(self) -> None:
        self._dispatcher = EventDispatcher()
        self._session_manager = SessionManager(settings, self._dispatcher)
        self._registry = ToolRegistry(self._session_manager)
        self._initialized = False
        self._running = False

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #

    async def run(self) -> None:
        """Start the server – read stdin line-by-line until EOF."""
        self._running = True
        await self._dispatcher.start()
        logger.info("%s v%s starting (MCP %s)", SERVER_NAME, SERVER_VERSION, PROTOCOL_VERSION)

        loop = asyncio.get_running_loop()
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await loop.connect_read_pipe(lambda: protocol, sys.stdin)

        try:
            while self._running:
                try:
                    line = await reader.readline()
                    if not line:
                        logger.info("stdin closed – shutting down.")
                        break
                    await self._handle_raw(line.decode("utf-8").strip())
                except asyncio.CancelledError:
                    break
                except Exception as exc:
                    logger.exception("Unhandled error in read loop: %s", exc)
        finally:
            await self._shutdown()

    async def _shutdown(self) -> None:
        self._running = False
        await self._dispatcher.stop()
        self._session_manager.close_all()
        logger.info("Server shut down cleanly.")

    # ------------------------------------------------------------------ #
    # Message routing
    # ------------------------------------------------------------------ #

    async def _handle_raw(self, raw: str) -> None:
        """Parse raw JSON-RPC text and dispatch to the correct handler."""
        if not raw:
            return
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError as exc:
            _send(_err(None, -32700, f"Parse error: {exc}"))
            return

        request_id = msg.get("id")
        method = msg.get("method", "")
        params = msg.get("params", {})

        logger.debug("→ %s (id=%s)", method, request_id)

        # Notifications (no id) – acknowledge silently
        if request_id is None and method.startswith("notifications/"):
            return

        try:
            result = await self._dispatch(method, params)
            _send(_ok(request_id, result))
            logger.debug("← %s OK", method)
        except SeleniumMCPError as exc:
            logger.warning("Tool error [%s]: %s", method, exc)
            _send(_err(request_id, -32000, str(exc), {"session_id": exc.session_id}))
        except KeyError as exc:
            _send(_err(request_id, -32601, f"Method not found: {exc}"))
        except TypeError as exc:
            _send(_err(request_id, -32602, f"Invalid params: {exc}"))
        except Exception as exc:
            logger.exception("Internal error [%s]", method)
            _send(_err(request_id, -32603, f"Internal error: {exc}"))

    async def _dispatch(self, method: str, params: dict) -> Any:
        """Route a JSON-RPC method to the appropriate MCP handler."""
        if method == "initialize":
            return self._handle_initialize(params)
        if method == "initialized":
            return {}
        if method == "ping":
            return {}
        if method == "tools/list":
            return self._handle_tools_list()
        if method == "tools/call":
            return await self._handle_tools_call(params)
        if method == "resources/list":
            return {"resources": []}
        if method == "prompts/list":
            return {"prompts": []}
        raise KeyError(method)

    # ------------------------------------------------------------------ #
    # MCP method handlers
    # ------------------------------------------------------------------ #

    def _handle_initialize(self, params: dict) -> dict:
        """Respond to the MCP initialize handshake."""
        client_info = params.get("clientInfo", {})
        logger.info(
            "Client connected: %s %s",
            client_info.get("name", "unknown"),
            client_info.get("version", ""),
        )
        self._initialized = True
        return {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {
                "tools": {"listChanged": False},
                "resources": {},
                "prompts": {},
                "logging": {},
            },
            "serverInfo": {
                "name": SERVER_NAME,
                "version": SERVER_VERSION,
            },
        }

    def _handle_tools_list(self) -> dict:
        """Return the list of available MCP tools."""
        return {"tools": self._registry.list_tools()}

    async def _handle_tools_call(self, params: dict) -> dict:
        """Execute a tool and wrap the result in MCP content format."""
        tool_name: str = params.get("name", "")
        arguments: dict = params.get("arguments", {})

        if not tool_name:
            raise TypeError("Missing 'name' in tools/call params")

        if tool_name not in {t["name"] for t in self._registry.list_tools()}:
            raise KeyError(repr(tool_name))

        logger.info("Calling tool: %s %s", tool_name, list(arguments.keys()))

        # Run synchronous tool calls in a thread pool to avoid blocking the event loop
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None, self._registry.call, tool_name, arguments
        )

        # Format as MCP content array
        content = [
            {
                "type": "text",
                "text": json.dumps(result, ensure_ascii=False, default=str),
            }
        ]

        # If the result contains base64 image data, also add an image content block
        if isinstance(result, dict) and "image_base64" in result:
            content.append(
                {
                    "type": "image",
                    "data": result["image_base64"],
                    "mimeType": result.get("mime_type", "image/png"),
                }
            )

        return {"content": content, "isError": False}


# ──────────────────────────────────────────────────────────────────────────────
# Entrypoint
# ──────────────────────────────────────────────────────────────────────────────

def main() -> None:
    """Start the MCP server."""
    # Reconfigure stdout to be unbuffered / line-buffered for JSON-RPC framing
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)

    server = MCPServer()
    try:
        asyncio.run(server.run())
    except KeyboardInterrupt:
        logger.info("Interrupted by user.")


if __name__ == "__main__":
    main()
