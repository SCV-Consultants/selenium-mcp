"""Session data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class BrowserType(str, Enum):
    """Supported browser types."""

    CHROME = "chrome"
    FIREFOX = "firefox"


class SessionStatus(str, Enum):
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
    created_at: datetime = field(default_factory=datetime.utcnow)
    current_url: Optional[str] = None
    error_message: Optional[str] = None

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
