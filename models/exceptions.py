"""Custom exception hierarchy for the selenium-mcp server."""

from __future__ import annotations


class SeleniumMCPError(Exception):
    """Base exception for all selenium-mcp errors."""

    def __init__(self, message: str, session_id: str | None = None) -> None:
        super().__init__(message)
        self.session_id = session_id


class SessionNotFoundError(SeleniumMCPError):
    """Raised when an operation targets a non-existent session."""


class SessionCreationError(SeleniumMCPError):
    """Raised when a browser session cannot be created."""


class SessionLimitError(SeleniumMCPError):
    """Raised when maximum concurrent sessions are exceeded."""


class ElementNotFoundError(SeleniumMCPError):
    """Raised when a CSS/XPath selector matches no element."""

    def __init__(self, selector: str, session_id: str | None = None) -> None:
        super().__init__(f"Element not found: {selector!r}", session_id)
        self.selector = selector


class ElementInteractionError(SeleniumMCPError):
    """Raised when an element cannot be interacted with (e.g. not clickable)."""


class NavigationError(SeleniumMCPError):
    """Raised when page navigation fails."""


class ScriptExecutionError(SeleniumMCPError):
    """Raised when JavaScript execution fails inside the browser."""


class ScreenshotError(SeleniumMCPError):
    """Raised when capturing a screenshot fails."""


class NetworkInterceptionError(SeleniumMCPError):
    """Raised when network interception cannot be set up or torn down."""


class BiDiNotSupportedError(SeleniumMCPError):
    """Raised when BiDi features are requested but not available."""


class TimeoutError(SeleniumMCPError):  # noqa: A001
    """Raised when a wait condition is not met within the given timeout."""

    def __init__(self, condition: str, timeout: float, session_id: str | None = None) -> None:
        super().__init__(f"Timed out after {timeout}s waiting for: {condition}", session_id)
        self.condition = condition
        self.timeout = timeout


class ConfigurationError(SeleniumMCPError):
    """Raised when the server configuration is invalid."""
