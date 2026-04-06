"""Session data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum


class BrowserType(StrEnum):
    """Supported browser types."""

    CHROME = "chrome"
    FIREFOX = "firefox"


class SessionStatus(StrEnum):
    """Possible session lifecycle states."""

    INITIALIZING = "initializing"
    READY = "ready"
    BUSY = "busy"
    ERROR = "error"
    CLOSED = "closed"


@dataclass
class SessionInfo:
    """Metadata about an active browser session."""

    session_id: str
    browser: BrowserType
    headless: bool
    status: SessionStatus = SessionStatus.INITIALIZING
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    current_url: str | None = None
    error_message: str | None = None

    def to_dict(self) -> dict:
        """Serialize to plain dict for MCP responses."""
        return {
            "session_id": self.session_id,
            "browser": self.browser.value,
            "headless": self.headless,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "current_url": self.current_url,
            "error_message": self.error_message,
        }
