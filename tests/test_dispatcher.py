"""Unit tests for the async event dispatcher."""

from __future__ import annotations

import asyncio
import pytest

from events.dispatcher import EventDispatcher
from models.events import ConsoleLogEvent, EventType


@pytest.mark.asyncio
async def test_publish_and_receive():
    """Published events are delivered to subscribers."""
    dispatcher = EventDispatcher()
    received: list = []

    async def handler(event):
        received.append(event)

    dispatcher.subscribe(EventType.CONSOLE_LOG, handler)
    await dispatcher.start()

    event = ConsoleLogEvent(session_id="s1", level="log", message="hello")
    await dispatcher.publish(event)

    await asyncio.sleep(0.2)
    await dispatcher.stop()

    assert len(received) == 1
    assert received[0].data["message"] == "hello"


@pytest.mark.asyncio
async def test_unsubscribe():
    """Unsubscribed handlers no longer receive events."""
    dispatcher = EventDispatcher()
    received: list = []

    async def handler(event):
        received.append(event)

    dispatcher.subscribe(EventType.CONSOLE_LOG, handler)
    dispatcher.unsubscribe(EventType.CONSOLE_LOG, handler)

    await dispatcher.start()
    await dispatcher.publish(ConsoleLogEvent(session_id="s1", level="log", message="x"))
    await asyncio.sleep(0.2)
    await dispatcher.stop()

    assert received == []


@pytest.mark.asyncio
async def test_multiple_event_types():
    """Handlers only receive events for their subscribed type."""
    dispatcher = EventDispatcher()
    console_received: list = []
    network_received: list = []

    async def console_handler(event):
        console_received.append(event)

    async def network_handler(event):
        network_received.append(event)

    dispatcher.subscribe(EventType.CONSOLE_LOG, console_handler)
    dispatcher.subscribe(EventType.NETWORK_REQUEST, network_handler)

    await dispatcher.start()

    from models.events import NetworkRequestEvent
    await dispatcher.publish(ConsoleLogEvent(session_id="s1", level="log", message="c"))
    await dispatcher.publish(NetworkRequestEvent(session_id="s1", request_id="r1", url="http://x.com"))

    await asyncio.sleep(0.2)
    await dispatcher.stop()

    assert len(console_received) == 1
    assert len(network_received) == 1


@pytest.mark.asyncio
async def test_queue_full_does_not_crash():
    """Overfilling the queue logs a warning but does not raise."""
    dispatcher = EventDispatcher(queue_maxsize=2)
    await dispatcher.start()

    for _ in range(10):
        await dispatcher.publish(ConsoleLogEvent(session_id="s1", level="log", message="spam"))

    await asyncio.sleep(0.2)
    await dispatcher.stop()
