"""Unit tests for configuration loading."""

from __future__ import annotations

import pytest
import yaml

from config.settings import Settings
from models.exceptions import ConfigurationError


class TestSettingsDefaults:
    def test_default_browser(self):
        s = Settings()
        assert s.default_browser == "chrome"

    def test_default_headless(self):
        s = Settings()
        assert s.headless is True

    def test_default_max_sessions(self):
        s = Settings()
        assert s.max_sessions == 5

    def test_default_bidi_enabled(self):
        s = Settings()
        assert s.bidi_enabled is True

    def test_window_size_list(self):
        s = Settings()
        w, h = s.window_size
        assert w == 1920
        assert h == 1080


class TestSettingsFromYAML:
    def test_yaml_override(self, tmp_path):
        cfg = tmp_path / "cfg.yaml"
        cfg.write_text(yaml.dump({"browser": {"default": "firefox", "headless": False}}))
        s = Settings(config_file=cfg)
        assert s.default_browser == "firefox"
        assert s.headless is False

    def test_invalid_yaml_raises(self, tmp_path):
        bad = tmp_path / "bad.yaml"
        bad.write_text("key: [unclosed")
        with pytest.raises(ConfigurationError):
            Settings(config_file=bad)


class TestSettingsFromEnv:
    def test_env_browser_override(self, monkeypatch):
        monkeypatch.setenv("SMCP_BROWSER", "firefox")
        s = Settings()
        assert s.default_browser == "firefox"

    def test_env_headless_false(self, monkeypatch):
        monkeypatch.setenv("SMCP_HEADLESS", "false")
        s = Settings()
        assert s.headless is False

    def test_env_debug_true(self, monkeypatch):
        monkeypatch.setenv("SMCP_DEBUG", "1")
        s = Settings()
        assert s.debug is True

    def test_env_max_sessions(self, monkeypatch):
        monkeypatch.setenv("SMCP_MAX_SESSIONS", "10")
        s = Settings()
        assert s.max_sessions == 10
