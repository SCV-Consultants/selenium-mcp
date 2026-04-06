"""Element interaction MCP tools (click, type, get_text, wait_for)."""

from __future__ import annotations

import logging

from tools.base import BaseTool, with_error_screenshot

logger = logging.getLogger("selenium_mcp.tools.interaction")


class InteractionTools(BaseTool):
    """MCP tools for interacting with page elements."""

    @with_error_screenshot
    def click(self, selector: str, session_id: str | None = None) -> dict:
        """
        Click the DOM element matched by *selector* (CSS selector).

        Args:
            selector:   CSS selector string.
            session_id: Session to target; auto-selected if only one exists.
        """
        session = self._get_session(session_id)
        session.click(selector)
        return {"success": True, "session_id": session.session_id, "selector": selector}

    @with_error_screenshot
    def type_text(
        self,
        selector: str,
        text: str,
        session_id: str | None = None,
    ) -> dict:
        """
        Clear *selector* and type *text* into it.

        Args:
            selector:   CSS selector of the input field.
            text:       Text to type.
            session_id: Session to target.
        """
        session = self._get_session(session_id)
        session.type_text(selector, text)
        return {
            "success": True,
            "session_id": session.session_id,
            "selector": selector,
            "characters_typed": len(text),
        }

    @with_error_screenshot
    def get_text(self, selector: str, session_id: str | None = None) -> dict:
        """
        Return the visible inner text of *selector*.

        Returns:
            dict with ``text`` key.
        """
        session = self._get_session(session_id)
        text = session.get_text(selector)
        return {
            "success": True,
            "session_id": session.session_id,
            "selector": selector,
            "text": text,
        }

    @with_error_screenshot
    def wait_for(
        self,
        selector: str,
        timeout: float = 10.0,
        session_id: str | None = None,
    ) -> dict:
        """
        Wait until *selector* is visible on the page.

        Args:
            selector: CSS selector to wait for.
            timeout:  Maximum wait time in seconds (default 10).
            session_id: Session to target.
        """
        session = self._get_session(session_id)
        session.wait_for(selector, timeout)
        return {
            "success": True,
            "session_id": session.session_id,
            "selector": selector,
            "timeout": timeout,
        }

    @with_error_screenshot
    def wait_for_dom_stable(
        self,
        timeout: float = 5.0,
        session_id: str | None = None,
    ) -> dict:
        """
        Smart DOM-stability wait – polls until the DOM stops mutating.

        Useful after AJAX-heavy interactions to avoid flaky selectors.

        Args:
            timeout:    Max time to wait in seconds.
            session_id: Session to target.
        """
        session = self._get_session(session_id)
        session.wait_for_dom_stable(timeout=timeout)
        return {"success": True, "session_id": session.session_id}

    @with_error_screenshot
    def get_attribute(
        self,
        selector: str,
        attribute: str,
        session_id: str | None = None,
    ) -> dict:
        """
        Get an attribute value from a DOM element.

        Args:
            selector:  CSS selector of the element.
            attribute: Attribute name (e.g. "href", "value", "class").
            session_id: Session to target.
        """
        session = self._get_session(session_id)
        value = session.get_attribute(selector, attribute)
        return {
            "success": True,
            "session_id": session.session_id,
            "selector": selector,
            "attribute": attribute,
            "value": value,
        }

    @with_error_screenshot
    def press_key(
        self,
        key: str,
        selector: str | None = None,
        session_id: str | None = None,
    ) -> dict:
        """
        Press a keyboard key.

        Args:
            key:        Key name (e.g. "Enter", "Tab", "Escape", "a").
            selector:   Optional CSS selector to send the key to.
            session_id: Session to target.
        """
        session = self._get_session(session_id)
        session.press_key(key, selector=selector)
        return {
            "success": True,
            "session_id": session.session_id,
            "key": key,
        }
