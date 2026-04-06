"""Cookie management MCP tools."""

from __future__ import annotations

import logging

from tools.base import BaseTool, with_error_screenshot

logger = logging.getLogger("selenium_mcp.tools.cookie")


class CookieTools(BaseTool):
    """MCP tools for browser cookie management."""

    @with_error_screenshot
    def add_cookie(
        self,
        name: str,
        value: str,
        domain: str | None = None,
        path: str | None = None,
        secure: bool | None = None,
        http_only: bool | None = None,
        session_id: str | None = None,
    ) -> dict:
        """
        Add a cookie. Browser must be on a page from the cookie's domain.

        Args:
            name:      Cookie name.
            value:     Cookie value.
            domain:    Cookie domain (optional).
            path:      Cookie path (optional).
            secure:    Secure flag (optional).
            http_only: HttpOnly flag (optional).
            session_id: Session to target.
        """
        session = self._get_session(session_id)
        kwargs = {}
        if domain is not None:
            kwargs["domain"] = domain
        if path is not None:
            kwargs["path"] = path
        if secure is not None:
            kwargs["secure"] = secure
        if http_only is not None:
            kwargs["httpOnly"] = http_only
        session.add_cookie(name, value, **kwargs)
        return {
            "success": True,
            "session_id": session.session_id,
            "cookie": name,
        }

    def get_cookies(
        self,
        name: str | None = None,
        session_id: str | None = None,
    ) -> dict:
        """
        Get cookies. Returns all or a specific one by name.

        Args:
            name:       Cookie name to filter (optional, returns all if omitted).
            session_id: Session to target.
        """
        session = self._get_session(session_id)
        cookies = session.get_cookies(name)
        return {
            "success": True,
            "session_id": session.session_id,
            "count": len(cookies),
            "cookies": cookies,
        }

    @with_error_screenshot
    def delete_cookie(
        self,
        name: str | None = None,
        session_id: str | None = None,
    ) -> dict:
        """
        Delete cookies. Deletes all or a specific one by name.

        Args:
            name:       Cookie name to delete (optional, deletes all if omitted).
            session_id: Session to target.
        """
        session = self._get_session(session_id)
        session.delete_cookies(name)
        return {
            "success": True,
            "session_id": session.session_id,
            "deleted": name or "all",
        }
