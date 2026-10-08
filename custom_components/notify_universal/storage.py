"""Persistent storage for Notify Universal."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN


STORAGE_VERSION = 1
STORAGE_KEY = f"{DOMAIN}.queue"


class NotifyUniversalStorage:
    """Persistent storage for the Notify Universal queue."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize persistent storage."""

        self.hass = hass
        self._store = Store(
            hass,
            STORAGE_VERSION,
            STORAGE_KEY,
        )
        self._queue: list[dict[str, Any]] = []

    async def async_load(self) -> list[dict[str, Any]]:
        """Load the notification queue from persistent storage."""

        data = await self._store.async_load()

        if not isinstance(data, dict):
            self._queue = []
            return self._queue

        queue = data.get("queue", [])

        if not isinstance(queue, list):
            self._queue = []
            return self._queue

        self._queue = [
            item
            for item in queue
            if isinstance(item, dict)
        ]

        return self._queue

    async def async_save(self) -> None:
        """Save the notification queue to persistent storage."""

        await self._store.async_save(
            {
                "queue": self._queue,
            }
        )

    async def async_add(
        self,
        item: dict[str, Any],
    ) -> None:
        """Add a notification to the persistent queue."""

        self._queue.append(item)
        await self.async_save()

    async def async_remove_first(self) -> dict[str, Any] | None:
        """Remove and return the first notification from the queue."""

        if not self._queue:
            return None

        item = self._queue.pop(0)
        await self.async_save()

        return item

    async def async_clear(self) -> None:
        """Clear the entire notification queue."""

        self._queue = []
        await self.async_save()

    @property
    def queue(self) -> list[dict[str, Any]]:
        """Return the current notification queue."""

        return list(self._queue)

    @property
    def size(self) -> int:
        """Return the number of queued notifications."""

        return len(self._queue)
