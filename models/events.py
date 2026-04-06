"""Event data models for BiDi event system."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class EventType(StrEnum):
    """Supported BiDi event categories."""

    CONSOLE_LOG = "console.log"
    NETWORK_REQUEST = "network.request"
    NETWORK_RESPONSE = "network.response"
    NETWORK_FAILED = "network.failed"
    DOM_MUTATION = "dom.mutation"
    PAGE_LOAD = "page.load"
    SCRIPT_ERROR = "script.error"


def _utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass
class BrowserEvent:
    """Generic browser event emitted by BiDi listeners."""

    session_id: str
    event_type: EventType = EventType.CONSOLE_LOG
    timestamp: datetime = field(default_factory=_utcnow)
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "event_type": self.event_type.value,
            "session_id": self.session_id,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
        }


@dataclass
class ConsoleLogEvent(BrowserEvent):
    """Console log message from the browser."""

    level: str = "log"
    message: str = ""
    source: str | None = None

    def __post_init__(self) -> None:
        self.event_type = EventType.CONSOLE_LOG
        self.data = {
            "level": self.level,
            "message": self.message,
            "source": self.source,
        }


@dataclass
class NetworkRequestEvent(BrowserEvent):
    """Outgoing network request captured by BiDi."""

    request_id: str = ""
    url: str = ""
    method: str = "GET"
    headers: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.event_type = EventType.NETWORK_REQUEST
        self.data = {
            "request_id": self.request_id,
            "url": self.url,
            "method": self.method,
            "headers": self.headers,
        }


@dataclass
class NetworkResponseEvent(BrowserEvent):
    """Network response captured by BiDi."""

    request_id: str = ""
    url: str = ""
    status: int = 0
    headers: dict[str, str] = field(default_factory=dict)
    body: str | None = None

    def __post_init__(self) -> None:
        self.event_type = EventType.NETWORK_RESPONSE
        self.data = {
            "request_id": self.request_id,
            "url": self.url,
            "status": self.status,
            "headers": self.headers,
            "body": self.body,
        }
