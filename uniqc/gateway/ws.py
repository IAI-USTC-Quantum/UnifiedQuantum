"""WebSocket event broadcaster for the gateway dashboard."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import WebSocket

# ---------------------------------------------------------------------------
# Event types
# ---------------------------------------------------------------------------

EventType = str

PAYLOAD = dict[str, Any]


class Event:
    """One broadcast event."""

    __slots__ = ("type", "payload")

    def __init__(self, type: EventType, payload: PAYLOAD) -> None:
        self.type = type
        self.payload = payload

    def to_json(self) -> str:
        return json.dumps({"type": self.type, "payload": self.payload})


# ---------------------------------------------------------------------------
# Broadcaster
# ---------------------------------------------------------------------------

PAYLOAD_BROADCAST = tuple[WebSocket, Event]


class EventBroadcaster:
    """ASGI-safe singleton that fans out events to all connected WebSocket clients.

    Usage::

        broadcaster = EventBroadcaster()
        # In a route handler:
        await broadcaster.broadcast(Event("task:updated", {"task_id": "abc"}))
    """

    def __init__(self) -> None:
        self._connections: list[WebSocket] = []
        self._queue: asyncio.Queue[PAYLOAD_BROADCAST] = asyncio.Queue()
        self._runner_task: asyncio.Task[None] | None = None

    # -- connection management ------------------------------------------------

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.append(websocket)
        # Start the background fan-out task on first connection
        if self._runner_task is None or self._runner_task.done():
            self._runner_task = asyncio.create_task(self._run())

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self._connections:
            self._connections.remove(websocket)

    # -- fan-out -------------------------------------------------------------

    async def broadcast(self, event: Event) -> None:
        """Enqueue an event for fan-out to all connected clients."""
        for conn in self._connections:
            await self._queue.put((conn, event))

    async def _run(self) -> None:
        """Background task: drain the queue, sending each event to every client."""
        while True:
            dead: list[WebSocket] = []

            # Collect all pending events
            pending: list[tuple[WebSocket, Event]] = []
            try:
                while True:
                    item = await asyncio.wait_for(self._queue.get(), timeout=0.05)
                    pending.append(item)
            except asyncio.TimeoutError:
                pass

            for ws, evt in pending:
                try:
                    await ws.send_text(evt.to_json())
                except Exception:
                    dead.append(ws)

            for ws in dead:
                self.disconnect(ws)

            if not self._connections and self._queue.empty():
                # No clients: stop the runner
                break

    # -- convenience helpers --------------------------------------------------

    async def emit_task_updated(self, task_id: str, status: str) -> None:
        await self.broadcast(
            Event("task:updated", {"task_id": task_id, "status": status})
        )

    async def emit_backend_status(
        self, backend_id: str, status: str
    ) -> None:
        await self.broadcast(
            Event("backend:status", {"backend_id": backend_id, "status": status})
        )


# Global singleton
broadcaster = EventBroadcaster()
