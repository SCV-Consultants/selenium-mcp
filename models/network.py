"""Network interception and log data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class NetworkLog:
    """Captured HTTP request/response pair."""

    request_id: str
    url: str
    method: str
    request_headers: dict[str, str] = field(default_factory=dict)
    request_body: str | None = None
    response_status: int | None = None
    response_headers: dict[str, str] = field(default_factory=dict)
    response_body: str | None = None
    duration_ms: float | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    error: str | None = None

    def to_dict(self) -> dict:
        return {
            "request_id": self.request_id,
            "url": self.url,
            "method": self.method,
            "request_headers": self.request_headers,
            "request_body": self.request_body,
            "response_status": self.response_status,
            "response_headers": self.response_headers,
            "response_body": self.response_body,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp.isoformat(),
            "error": self.error,
        }


@dataclass
class InterceptRule:
    """URL interception rule for request blocking or modification."""

    pattern: str
    action: str = "log"  # log | block | modify
    modify_response: dict[str, Any] | None = None
    active: bool = True

    def to_dict(self) -> dict:
        return {
            "pattern": self.pattern,
            "action": self.action,
            "modify_response": self.modify_response,
            "active": self.active,
        }


@dataclass
class ConsoleLog:
    """Single console log entry from the browser."""

    level: str
    message: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    source: str | None = None
    line_number: int | None = None
    column_number: int | None = None

    def to_dict(self) -> dict:
        return {
            "level": self.level,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "line_number": self.line_number,
            "column_number": self.column_number,
        }


@dataclass
class PerformanceMetrics:
    """Browser performance timing snapshot."""

    navigation_start: float = 0.0
    dom_content_loaded: float = 0.0
    dom_complete: float = 0.0
    load_event_end: float = 0.0
    first_paint: float | None = None
    first_contentful_paint: float | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "navigation_start": self.navigation_start,
            "dom_content_loaded": self.dom_content_loaded,
            "dom_complete": self.dom_complete,
            "load_event_end": self.load_event_end,
            "first_paint": self.first_paint,
            "first_contentful_paint": self.first_contentful_paint,
        }
