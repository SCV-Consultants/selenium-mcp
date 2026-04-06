"""Unit tests for SessionManager using mocked WebDrivers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from config.settings import Settings
from driver.session_manager import SessionManager
from events.dispatcher import EventDispatcher
from models.exceptions import SessionLimitError, SessionNotFoundError


def _make_manager(max_sessions: int = 3) -> SessionManager:
    s = Settings()
    s._data["browser"]["max_sessions"] = max_sessions
    dispatcher = EventDispatcher()
    return SessionManager(s, dispatcher)


def _mock_driver():
    driver = MagicMock()
    driver.current_url = "about:blank"
    driver.get_screenshot_as_base64.return_value = "base64data"
    driver.page_source = "<html></html>"
    driver.get_log.return_value = []
    return driver


class TestSessionManager:
    @patch("driver.session_manager.build_driver")
    def test_create_session_returns_session(self, mock_build):
        mock_build.return_value = _mock_driver()
        mgr = _make_manager()
        session = mgr.create_session(browser="chrome", headless=True)
        assert session.session_id
        assert len(mgr) == 1

    @patch("driver.session_manager.build_driver")
    def test_create_multiple_sessions(self, mock_build):
        mock_build.return_value = _mock_driver()
        mgr = _make_manager(max_sessions=3)
        s1 = mgr.create_session()
        s2 = mgr.create_session()
        assert len(mgr) == 2
        assert s1.session_id != s2.session_id

    @patch("driver.session_manager.build_driver")
    def test_session_limit_raises(self, mock_build):
        mock_build.return_value = _mock_driver()
        mgr = _make_manager(max_sessions=1)
        mgr.create_session()
        with pytest.raises(SessionLimitError):
            mgr.create_session()

    @patch("driver.session_manager.build_driver")
    def test_get_session_valid(self, mock_build):
        mock_build.return_value = _mock_driver()
        mgr = _make_manager()
        s = mgr.create_session()
        found = mgr.get_session(s.session_id)
        assert found.session_id == s.session_id

    def test_get_session_invalid_raises(self):
        mgr = _make_manager()
        with pytest.raises(SessionNotFoundError):
            mgr.get_session("nonexistent-id")

    @patch("driver.session_manager.build_driver")
    def test_close_session(self, mock_build):
        mock_build.return_value = _mock_driver()
        mgr = _make_manager()
        s = mgr.create_session()
        mgr.close_session(s.session_id)
        assert len(mgr) == 0

    @patch("driver.session_manager.build_driver")
    def test_get_or_default_single_session(self, mock_build):
        mock_build.return_value = _mock_driver()
        mgr = _make_manager()
        s = mgr.create_session()
        found = mgr.get_or_default()
        assert found.session_id == s.session_id

    @patch("driver.session_manager.build_driver")
    def test_get_or_default_auto_creates(self, mock_build):
        mock_build.return_value = _mock_driver()
        mgr = _make_manager()
        s = mgr.get_or_default()
        assert s is not None
        assert len(mgr) == 1

    @patch("driver.session_manager.build_driver")
    def test_list_sessions(self, mock_build):
        mock_build.return_value = _mock_driver()
        mgr = _make_manager()
        mgr.create_session()
        mgr.create_session()
        sessions = mgr.list_sessions()
        assert len(sessions) == 2
        assert all("session_id" in s for s in sessions)

    @patch("driver.session_manager.build_driver")
    def test_close_all(self, mock_build):
        mock_build.return_value = _mock_driver()
        mgr = _make_manager()
        mgr.create_session()
        mgr.create_session()
        mgr.close_all()
        assert len(mgr) == 0
