"""Unit tests for MCP tool implementations (using mocked sessions)."""

from __future__ import annotations

from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from config.settings import Settings
from driver.session_manager import SessionManager
from events.dispatcher import EventDispatcher
from models.exceptions import ElementNotFoundError, NavigationError
from models.network import PerformanceMetrics
from models.session import BrowserType, SessionInfo, SessionStatus
from tools.interaction_tools import InteractionTools
from tools.log_tools import LogTools
from tools.navigation_tools import NavigationTools
from tools.registry import ToolRegistry
from tools.script_tools import ScriptTools
from tools.session_tools import SessionTools


def _make_mock_session(session_id: str = "test-session-1"):
    """Create a fully mocked BrowserSession."""
    session = MagicMock()
    session.session_id = session_id
    info = SessionInfo(
        session_id=session_id,
        browser=BrowserType.CHROME,
        headless=True,
        status=SessionStatus.READY,
        current_url="https://example.com",
    )
    type(session).info = PropertyMock(return_value=info)
    session.get_dom.return_value = "<html><body>Hello</body></html>"
    session.get_text.return_value = "Hello World"
    session.screenshot.return_value = "base64encodedpng=="
    session.execute_js.return_value = {"result": 42}
    session.get_console_logs.return_value = [
        {"level": "log", "message": "test message", "timestamp": "2024-01-01T00:00:00"}
    ]
    session.get_network_logs.return_value = [
        {"request_id": "r1", "url": "https://api.example.com", "method": "GET"}
    ]
    session.get_performance_metrics.return_value = PerformanceMetrics(
        dom_complete=1500.0, load_event_end=1600.0
    )
    return session


def _make_manager_with_mock_session():
    """Return a (SessionManager, mock_session) pair."""
    s = Settings()
    dispatcher = EventDispatcher()
    mgr = SessionManager(s, dispatcher)

    mock_session = _make_mock_session()
    mgr._sessions["test-session-1"] = mock_session
    return mgr, mock_session


class TestNavigationTools:
    def test_open_page(self):
        mgr, session = _make_manager_with_mock_session()
        tool = NavigationTools(mgr)
        result = tool.open_page("https://example.com", session_id="test-session-1")
        session.open_page.assert_called_once_with("https://example.com")
        assert result["success"] is True

    def test_navigate_back(self):
        mgr, session = _make_manager_with_mock_session()
        tool = NavigationTools(mgr)
        result = tool.navigate_back(session_id="test-session-1")
        session.navigate_back.assert_called_once()
        assert result["success"] is True

    def test_navigate_forward(self):
        mgr, session = _make_manager_with_mock_session()
        tool = NavigationTools(mgr)
        result = tool.navigate_forward(session_id="test-session-1")
        session.navigate_forward.assert_called_once()
        assert result["success"] is True

    def test_get_dom(self):
        mgr, session = _make_manager_with_mock_session()
        tool = NavigationTools(mgr)
        result = tool.get_dom(session_id="test-session-1")
        assert "Hello" in result["html"]
        assert result["length"] > 0

    def test_open_page_propagates_error(self):
        mgr, session = _make_manager_with_mock_session()
        session.open_page.side_effect = NavigationError("failed", "test-session-1")
        tool = NavigationTools(mgr)
        with pytest.raises(NavigationError):
            tool.open_page("https://bad.url", session_id="test-session-1")


class TestInteractionTools:
    def test_click(self):
        mgr, session = _make_manager_with_mock_session()
        tool = InteractionTools(mgr)
        result = tool.click(".btn", session_id="test-session-1")
        session.click.assert_called_once_with(".btn")
        assert result["success"] is True
        assert result["selector"] == ".btn"

    def test_type_text(self):
        mgr, session = _make_manager_with_mock_session()
        tool = InteractionTools(mgr)
        result = tool.type_text("#email", "user@test.com", session_id="test-session-1")
        session.type_text.assert_called_once_with("#email", "user@test.com")
        assert result["characters_typed"] == len("user@test.com")

    def test_get_text(self):
        mgr, session = _make_manager_with_mock_session()
        tool = InteractionTools(mgr)
        result = tool.get_text("h1", session_id="test-session-1")
        assert result["text"] == "Hello World"

    def test_wait_for(self):
        mgr, session = _make_manager_with_mock_session()
        tool = InteractionTools(mgr)
        result = tool.wait_for(".modal", timeout=5.0, session_id="test-session-1")
        session.wait_for.assert_called_once_with(".modal", 5.0)
        assert result["success"] is True

    def test_wait_for_dom_stable(self):
        mgr, session = _make_manager_with_mock_session()
        tool = InteractionTools(mgr)
        result = tool.wait_for_dom_stable(timeout=3.0, session_id="test-session-1")
        session.wait_for_dom_stable.assert_called_once_with(timeout=3.0)
        assert result["success"] is True

    def test_click_raises_element_not_found(self):
        mgr, session = _make_manager_with_mock_session()
        session.click.side_effect = ElementNotFoundError(".missing", "test-session-1")
        tool = InteractionTools(mgr)
        with pytest.raises(ElementNotFoundError):
            tool.click(".missing", session_id="test-session-1")


class TestScriptTools:
    def test_execute_js(self):
        mgr, session = _make_manager_with_mock_session()
        tool = ScriptTools(mgr)
        result = tool.execute_js("return 42;", session_id="test-session-1")
        session.execute_js.assert_called_once_with("return 42;")
        assert result["success"] is True
        assert result["result"] == {"result": 42}

    def test_screenshot(self):
        mgr, session = _make_manager_with_mock_session()
        tool = ScriptTools(mgr)
        result = tool.screenshot(session_id="test-session-1")
        assert result["image_base64"] == "base64encodedpng=="
        assert result["mime_type"] == "image/png"


class TestLogTools:
    def test_get_console_logs(self):
        mgr, session = _make_manager_with_mock_session()
        tool = LogTools(mgr)
        result = tool.get_console_logs(session_id="test-session-1")
        assert result["count"] == 1
        assert result["logs"][0]["level"] == "log"

    def test_get_network_logs(self):
        mgr, session = _make_manager_with_mock_session()
        tool = LogTools(mgr)
        result = tool.get_network_logs(session_id="test-session-1")
        assert result["count"] == 1
        assert result["logs"][0]["url"] == "https://api.example.com"

    def test_get_performance_metrics(self):
        mgr, session = _make_manager_with_mock_session()
        tool = LogTools(mgr)
        result = tool.get_performance_metrics(session_id="test-session-1")
        assert result["metrics"]["dom_complete"] == 1500.0

    def test_intercept_requests(self):
        mgr, session = _make_manager_with_mock_session()
        tool = LogTools(mgr)
        result = tool.intercept_requests("*api*", action="log", session_id="test-session-1")
        assert result["success"] is True
        assert result["rule"]["pattern"] == "*api*"


class TestSessionTools:
    @patch("driver.session_manager.build_driver")
    def test_create_session(self, mock_build):
        driver = MagicMock()
        driver.current_url = "about:blank"
        mock_build.return_value = driver
        s = Settings()
        dispatcher = EventDispatcher()
        mgr = SessionManager(s, dispatcher)
        tool = SessionTools(mgr)
        result = tool.create_session(browser="chrome", headless=True)
        assert result["success"] is True
        assert "session_id" in result["session"]

    def test_list_sessions(self):
        mgr, session = _make_manager_with_mock_session()
        tool = SessionTools(mgr)
        result = tool.list_sessions()
        assert result["count"] == 1
        assert result["sessions"][0]["session_id"] == "test-session-1"

    def test_close_session(self):
        mgr, session = _make_manager_with_mock_session()
        tool = SessionTools(mgr)
        result = tool.close_session("test-session-1")
        assert result["success"] is True
        assert result["status"] == "closed"


class TestToolRegistry:
    def test_list_tools_contains_required(self):
        s = Settings()
        dispatcher = EventDispatcher()
        mgr = SessionManager(s, dispatcher)
        registry = ToolRegistry(mgr)
        names = {t["name"] for t in registry.list_tools()}
        required = {
            "open_page", "click", "type_text", "get_text", "screenshot",
            "get_dom", "execute_js", "wait_for", "get_network_logs",
            "intercept_requests", "get_console_logs", "navigate_back",
            "navigate_forward",
        }
        assert required.issubset(names)

    def test_call_unknown_tool_raises(self):
        s = Settings()
        dispatcher = EventDispatcher()
        mgr = SessionManager(s, dispatcher)
        registry = ToolRegistry(mgr)
        with pytest.raises(KeyError):
            registry.call("nonexistent_tool", {})

    def test_tool_descriptor_has_required_fields(self):
        s = Settings()
        dispatcher = EventDispatcher()
        mgr = SessionManager(s, dispatcher)
        registry = ToolRegistry(mgr)
        for tool in registry.list_tools():
            assert "name" in tool
            assert "description" in tool
            assert "inputSchema" in tool
