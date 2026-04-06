"""Application settings loaded from ENV variables or a YAML config file."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from models.exceptions import ConfigurationError

_DEFAULT_CONFIG_PATH = Path(__file__).parent / "default.yaml"


class Settings:
    """
    Central configuration object.

    Priority (highest → lowest):
        1. Environment variables  (SMCP_*)
        2. YAML config file       (path from SMCP_CONFIG_FILE or config/default.yaml)
        3. Hard-coded defaults
    """

    # ------------------------------------------------------------------ #
    # Defaults
    # ------------------------------------------------------------------ #
    _DEFAULTS: dict[str, Any] = {
        "server": {
            "host": "127.0.0.1",
            "port": 8765,
            "log_level": "INFO",
            "debug": False,
        },
        "browser": {
            "default": "chrome",
            "headless": True,
            "max_sessions": 5,
            "implicit_wait": 5,
            "page_load_timeout": 30,
            "script_timeout": 10,
            "window_size": [1920, 1080],
        },
        "bidi": {
            "enabled": True,
            "console_events": True,
            "network_events": True,
        },
        "retry": {
            "max_attempts": 3,
            "backoff_seconds": 1.0,
        },
        "screenshot": {
            "on_error": True,
            "directory": "screenshots",
        },
    }

    def __init__(self, config_file: Path | None = None) -> None:
        self._data: dict[str, Any] = self._deep_copy(self._DEFAULTS)
        self._load_yaml(config_file)
        self._apply_env()

    # ------------------------------------------------------------------ #
    # Public accessors
    # ------------------------------------------------------------------ #

    @property
    def host(self) -> str:
        return self._get("server.host")

    @property
    def port(self) -> int:
        return int(self._get("server.port"))

    @property
    def log_level(self) -> str:
        return str(self._get("server.log_level")).upper()

    @property
    def debug(self) -> bool:
        return bool(self._get("server.debug"))

    @property
    def default_browser(self) -> str:
        return str(self._get("browser.default")).lower()

    @property
    def headless(self) -> bool:
        return bool(self._get("browser.headless"))

    @property
    def max_sessions(self) -> int:
        return int(self._get("browser.max_sessions"))

    @property
    def implicit_wait(self) -> float:
        return float(self._get("browser.implicit_wait"))

    @property
    def page_load_timeout(self) -> float:
        return float(self._get("browser.page_load_timeout"))

    @property
    def script_timeout(self) -> float:
        return float(self._get("browser.script_timeout"))

    @property
    def window_size(self) -> list[int]:
        raw = self._get("browser.window_size")
        return [int(raw[0]), int(raw[1])]

    @property
    def bidi_enabled(self) -> bool:
        return bool(self._get("bidi.enabled"))

    @property
    def bidi_console_events(self) -> bool:
        return bool(self._get("bidi.console_events"))

    @property
    def bidi_network_events(self) -> bool:
        return bool(self._get("bidi.network_events"))

    @property
    def retry_max_attempts(self) -> int:
        return int(self._get("retry.max_attempts"))

    @property
    def retry_backoff(self) -> float:
        return float(self._get("retry.backoff_seconds"))

    @property
    def screenshot_on_error(self) -> bool:
        return bool(self._get("screenshot.on_error"))

    @property
    def screenshot_directory(self) -> Path:
        return Path(self._get("screenshot.directory"))

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _get(self, dotted_key: str) -> Any:
        keys = dotted_key.split(".")
        node: Any = self._data
        for k in keys:
            if not isinstance(node, dict) or k not in node:
                raise ConfigurationError(f"Missing config key: {dotted_key!r}")
            node = node[k]
        return node

    def _set(self, dotted_key: str, value: Any) -> None:
        keys = dotted_key.split(".")
        node = self._data
        for k in keys[:-1]:
            node = node.setdefault(k, {})
        node[keys[-1]] = value

    def _load_yaml(self, path: Path | None) -> None:
        env_config = os.environ.get("SMCP_CONFIG_FILE", "")
        candidates = [
            path,
            Path(env_config) if env_config else None,
            _DEFAULT_CONFIG_PATH,
        ]
        for candidate in candidates:
            if candidate and candidate.is_file():
                try:
                    with candidate.open("r", encoding="utf-8") as fh:
                        data = yaml.safe_load(fh) or {}
                    self._merge(self._data, data)
                except yaml.YAMLError as exc:
                    raise ConfigurationError(f"Invalid YAML config: {exc}") from exc
                return

    def _apply_env(self) -> None:
        """Map SMCP_* environment variables onto the config tree."""
        mapping = {
            "SMCP_HOST": "server.host",
            "SMCP_PORT": "server.port",
            "SMCP_LOG_LEVEL": "server.log_level",
            "SMCP_DEBUG": "server.debug",
            "SMCP_BROWSER": "browser.default",
            "SMCP_HEADLESS": "browser.headless",
            "SMCP_MAX_SESSIONS": "browser.max_sessions",
            "SMCP_IMPLICIT_WAIT": "browser.implicit_wait",
            "SMCP_PAGE_LOAD_TIMEOUT": "browser.page_load_timeout",
            "SMCP_BIDI_ENABLED": "bidi.enabled",
            "SMCP_SCREENSHOT_ON_ERROR": "screenshot.on_error",
            "SMCP_SCREENSHOT_DIR": "screenshot.directory",
        }
        bool_keys = {"server.debug", "browser.headless", "bidi.enabled", "screenshot.on_error"}
        for env_key, config_key in mapping.items():
            raw = os.environ.get(env_key)
            if raw is None:
                continue
            if config_key in bool_keys:
                self._set(config_key, raw.lower() in {"1", "true", "yes"})
            else:
                self._set(config_key, raw)

    @staticmethod
    def _deep_copy(obj: Any) -> Any:
        import copy
        return copy.deepcopy(obj)

    @staticmethod
    def _merge(base: dict, override: dict) -> None:
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                Settings._merge(base[key], value)
            else:
                base[key] = value


# Singleton instance – import and use directly:  from config.settings import settings
settings = Settings()
