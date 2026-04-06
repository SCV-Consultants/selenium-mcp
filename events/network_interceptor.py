"""
Network request interceptor.

Uses Selenium 4 CDP (Chrome) or BiDi network interception to capture and
optionally block/modify HTTP traffic for the active session.
"""

from __future__ import annotations

import fnmatch
import logging
from typing import TYPE_CHECKING, Dict, List, Optional

from models.network import InterceptRule

if TYPE_CHECKING:
    from driver.session import BrowserSession

logger = logging.getLogger("selenium_mcp.events.network_interceptor")


class NetworkInterceptor:
    """
    Manages URL-pattern-based network interception for a BrowserSession.

    Currently implements:
    - **log** action: capture request/response metadata
    - **block** action: abort matching requests via CDP fetch interception

    The interceptor operates at the CDP level for Chrome and falls back to
    passive log collection for Firefox (BiDi network interception is still
    experimental in Firefox).
    """

    def __init__(self, session: "BrowserSession") -> None:
        self._session = session
        self._rules: Dict[str, InterceptRule] = {}
        self._cdp_enabled = False

    # ------------------------------------------------------------------ #
    # Rule management
    # ------------------------------------------------------------------ #

    def add_rule(self, pattern: str, action: str = "log") -> InterceptRule:
        """
        Register a new interception rule.

        Args:
            pattern: Glob-style URL pattern (e.g. ``"*.example.com/api/*"``).
            action:  One of ``log``, ``block``.

        Returns:
            The created InterceptRule.
        """
        rule = InterceptRule(pattern=pattern, action=action)
        self._rules[pattern] = rule
        self._session.add_intercept_pattern(pattern)
        self._apply_cdp_intercept()
        logger.info("[%s] Intercept rule added: %s → %s", self._session.session_id, pattern, action)
        return rule

    def remove_rule(self, pattern: str) -> None:
        """Remove an interception rule by pattern."""
        self._rules.pop(pattern, None)
        self._apply_cdp_intercept()

    def list_rules(self) -> List[dict]:
        return [r.to_dict() for r in self._rules.values()]

    # ------------------------------------------------------------------ #
    # CDP integration (Chrome only)
    # ------------------------------------------------------------------ #

    def _apply_cdp_intercept(self) -> None:
        """Push the current rule set to the browser via CDP Fetch domain."""
        try:
            driver = self._session.driver
            block_patterns = [
                {"urlPattern": r.pattern, "requestStage": "Request"}
                for r in self._rules.values()
                if r.action == "block" and r.active
            ]
            if block_patterns:
                driver.execute_cdp_cmd("Fetch.enable", {"patterns": block_patterns})
                self._cdp_enabled = True
                logger.debug("[%s] CDP Fetch interception enabled for %d pattern(s)",
                             self._session.session_id, len(block_patterns))
            elif self._cdp_enabled:
                driver.execute_cdp_cmd("Fetch.disable", {})
                self._cdp_enabled = False
        except Exception as exc:
            logger.debug("[%s] CDP Fetch not available: %s", self._session.session_id, exc)

    # ------------------------------------------------------------------ #
    # Pattern matching helper
    # ------------------------------------------------------------------ #

    def matches_any(self, url: str) -> Optional[InterceptRule]:
        """Return the first matching active rule for *url*, or None."""
        for rule in self._rules.values():
            if rule.active and fnmatch.fnmatch(url, rule.pattern):
                return rule
        return None
