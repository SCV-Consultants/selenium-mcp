"""Event data models for BiDi event system."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


class EventType(str, Enum):
    """Supported BiDi event categories."""

    CONSOLE_LOG = "console.log"
    NETWORK_REQUEST = "network.request"
    NETWORK_RESPONSE = "network.response"
    NETWORK_FAILED = "network.failed"
    DOM_MUTATION = "dom.mutation"
    PAGE_LOAD = "page.load"
    SCRIPT_ERROR = "script.error"


@dataclass
class BrowserEvent:
    """Generic browser event emitted by BiDi listeners."""

    event_type: EventType
    session_id: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    data: Dict[str, Any] = field(default_factory=dict)

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
    source: Optional[str] = None

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
    headers: Dict[str, str] = field(default_factory=dict)

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
    headers: Dict[str, str] = field(default_factory=dict)
    body: Optional[str] = None

    def __post_init__(self) -> None:
        self.event_type = EventType.NETWORK_RESPONSE
        self.data = {
            "request_id": self.request_id,
            "url": self.url,
            "status": self.status,
            "headers": self.headers,
            "body": self.body,
        }
