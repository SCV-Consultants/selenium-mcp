"""Unit tests for the models layer."""

from __future__ import annotations

from models.session import BrowserType, SessionInfo, SessionStatus
from models.events import (
    ConsoleLogEvent,
    EventType,
    NetworkRequestEvent,
    NetworkResponseEvent,
)
from models.network import NetworkLog, InterceptRule, ConsoleLog, PerformanceMetrics
from models.exceptions import (
    SeleniumMCPError,
    SessionNotFoundError,
    ElementNotFoundError,
    TimeoutError as MCPTimeoutError,
)


class TestSessionInfo:
    def test_to_dict_contains_required_keys(self):
        info = SessionInfo(
            session_id="abc-123",
            browser=BrowserType.CHROME,
            headless=True,
        )
        d = info.to_dict()
        assert d["session_id"] == "abc-123"
        assert d["browser"] == "chrome"
        assert d["headless"] is True
        assert d["status"] == "initializing"
        assert "created_at" in d

    def test_status_transition(self):
        info = SessionInfo(session_id="x", browser=BrowserType.FIREFOX, headless=False)
        info.status = SessionStatus.READY
        assert info.to_dict()["status"] == "ready"


class TestBrowserEvents:
    def test_console_log_event_fields(self):
        evt = ConsoleLogEvent(
            session_id="s1",
            level="warn",
            message="something broke",
            source="bidi",
        )
        assert evt.event_type == EventType.CONSOLE_LOG
        assert evt.data["level"] == "warn"
        assert evt.data["message"] == "something broke"

    def test_network_request_event(self):
        evt = NetworkRequestEvent(
            session_id="s1",
            request_id="r1",
            url="https://example.com/api",
            method="POST",
        )
        assert evt.event_type == EventType.NETWORK_REQUEST
        assert evt.data["method"] == "POST"

    def test_event_to_dict(self):
        evt = NetworkResponseEvent(
            session_id="s1",
            request_id="r1",
            url="https://example.com",
            status=200,
        )
        d = evt.to_dict()
        assert d["event_type"] == "network.response"
        assert isinstance(d["timestamp"], str)


class TestNetworkModels:
    def test_network_log_to_dict(self):
        log = NetworkLog(
            request_id="req-1",
            url="https://example.com",
            method="GET",
            response_status=200,
        )
        d = log.to_dict()
        assert d["url"] == "https://example.com"
        assert d["response_status"] == 200

    def test_intercept_rule_defaults(self):
        rule = InterceptRule(pattern="*example.com*")
        assert rule.action == "log"
        assert rule.active is True

    def test_console_log_to_dict(self):
        log = ConsoleLog(level="error", message="oops")
        d = log.to_dict()
        assert d["level"] == "error"

    def test_performance_metrics_to_dict(self):
        m = PerformanceMetrics(dom_complete=1200.0)
        d = m.to_dict()
        assert d["dom_complete"] == 1200.0


class TestExceptions:
    def test_base_exception_message(self):
        exc = SeleniumMCPError("test error", session_id="s1")
        assert str(exc) == "test error"
        assert exc.session_id == "s1"

    def test_element_not_found_message(self):
        exc = ElementNotFoundError(".my-button", session_id="s1")
        assert ".my-button" in str(exc)
        assert exc.selector == ".my-button"

    def test_session_not_found_inherits(self):
        exc = SessionNotFoundError("no session")
        assert isinstance(exc, SeleniumMCPError)

    def test_timeout_error_fields(self):
        exc = MCPTimeoutError("visibility of #modal", 10.0, "s1")
        assert "10.0" in str(exc)
        assert exc.timeout == 10.0
        assert exc.condition == "visibility of #modal"
