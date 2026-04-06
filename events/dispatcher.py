"""
Async event dispatcher – pub/sub hub for BiDi browser events.

Producers (BiDi listeners) push events via ``publish()``.
Consumers (MCP tools, log collectors) subscribe via ``subscribe()``.
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from collections.abc import Callable, Coroutine

from models.events import BrowserEvent, EventType

logger = logging.getLogger("selenium_mcp.events.dispatcher")

# Type alias for async handlers
AsyncHandler = Callable[[BrowserEvent], Coroutine]


class EventDispatcher:
    """
    Central async pub/sub dispatcher.

    Usage::

        dispatcher = EventDispatcher()

        # Subscribe
        async def my_handler(event: BrowserEvent) -> None:
            print(event)

        dispatcher.subscribe(EventType.CONSOLE_LOG, my_handler)

        # Publish (from sync context use publish_sync)
        await dispatcher.publish(event)
    """

    def __init__(self, queue_maxsize: int = 1000) -> None:
        self._handlers: dict[EventType, list[AsyncHandler]] = defaultdict(list)
        self._queue: asyncio.Queue[BrowserEvent] = asyncio.Queue(maxsize=queue_maxsize)
        self._running = False
        self._task: asyncio.Task | None = None

    # ------------------------------------------------------------------ #
    # Subscription API
    # ------------------------------------------------------------------ #

    def subscribe(self, event_type: EventType, handler: AsyncHandler) -> None:
        """Register *handler* for *event_type*."""
        self._handlers[event_type].append(handler)
        logger.debug("Handler registered for %s", event_type.value)

    def unsubscribe(self, event_type: EventType, handler: AsyncHandler) -> None:
        """Remove *handler* from *event_type* subscribers."""
        try:
            self._handlers[event_type].remove(handler)
        except ValueError:
            pass

    # ------------------------------------------------------------------ #
    # Publishing
    # ------------------------------------------------------------------ #

    async def publish(self, event: BrowserEvent) -> None:
        """Enqueue *event* for async delivery to all subscribers."""
        try:
            self._queue.put_nowait(event)
        except asyncio.QueueFull:
            logger.warning("Event queue full – dropping %s event", event.event_type.value)

    def publish_sync(
        self,
        event: BrowserEvent,
        loop: asyncio.AbstractEventLoop | None = None,
    ) -> None:
        """
        Thread-safe publish from a non-async context (e.g. Selenium callbacks).

        Uses ``call_soon_threadsafe`` if an event loop is provided/running.
        """
        try:
            target_loop = loop or asyncio.get_event_loop()
            target_loop.call_soon_threadsafe(self._queue.put_nowait, event)
        except RuntimeError:
            # No running loop – best effort synchronous dispatch
            try:
                self._queue.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning(
                    "Event queue full – dropping %s event (sync)",
                    event.event_type.value,
                )

    # ------------------------------------------------------------------ #
    # Dispatcher loop
    # ------------------------------------------------------------------ #

    async def start(self) -> None:
        """Start the background dispatch loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._dispatch_loop(), name="event-dispatcher")
        logger.info("Event dispatcher started.")

    async def stop(self) -> None:
        """Gracefully stop the dispatch loop."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Event dispatcher stopped.")

    async def _dispatch_loop(self) -> None:
        """Pull events from the queue and fan out to registered handlers."""
        while self._running:
            try:
                event = await asyncio.wait_for(self._queue.get(), timeout=0.5)
            except TimeoutError:
                continue

            handlers = self._handlers.get(event.event_type, [])
            for handler in handlers:
                try:
                    await handler(event)
                except Exception as exc:
                    logger.exception(
                        "Handler %s raised for %s: %s",
                        getattr(handler, "__name__", handler),
                        event.event_type.value,
                        exc,
                    )
            self._queue.task_done()
