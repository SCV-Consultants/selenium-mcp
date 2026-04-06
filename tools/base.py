"""Base class and shared utilities for MCP tool implementations."""

from __future__ import annotations

import functools
import logging
from typing import Any, Callable, Optional, TypeVar

from driver.session import BrowserSession
from driver.session_manager import SessionManager
from models.exceptions import SeleniumMCPError

logger = logging.getLogger("selenium_mcp.tools.base")

F = TypeVar("F", bound=Callable[..., Any])


def with_error_screenshot(method: F) -> F:
    """
    Decorator that captures a screenshot when an unhandled exception occurs.

    Expects the first argument to be a ``BrowserSession`` instance or that the
    bound method's class exposes a ``_session_manager`` attribute.
    """

    @functools.wraps(method)
    def wrapper(self: "BaseTool", *args: Any, **kwargs: Any) -> Any:
        session: Optional[BrowserSession] = None
        try:
            # Try to resolve the session from common keyword args
            session_id = kwargs.get("session_id")
            try:
                session = self._session_manager.get_or_default(session_id)
            except Exception:
                pass
            return method(self, *args, **kwargs)
        except SeleniumMCPError:
            if session:
                session.screenshot_on_error(label=method.__name__)
            raise
        except Exception as exc:
            if session:
                session.screenshot_on_error(label=method.__name__)
            raise SeleniumMCPError(f"Unexpected error in {method.__name__}: {exc}") from exc

    return wrapper  # type: ignore[return-value]


class BaseTool:
    """
    Abstract base for all MCP tool groups.

    Subclasses gain access to the shared SessionManager and Settings,
    and can use the ``with_error_screenshot`` decorator on their methods.
    """

    def __init__(self, session_manager: SessionManager) -> None:
        self._session_manager = session_manager

    def _get_session(self, session_id: Optional[str] = None) -> BrowserSession:
        """Resolve a session, auto-creating one if needed."""
        return self._session_manager.get_or_default(session_id)
