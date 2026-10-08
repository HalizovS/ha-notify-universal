"""Notification delivery for Notify Universal."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant


class NotifyUniversalNotifier:
    """Handle notification delivery."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the notifier."""

        self.hass = hass

    async def async_send_notify_entity(
        self,
        entity_id: str,
        title: str,
        message: str,
    ) -> bool:
        """Send a notification through a notify entity."""

        try:
            await self.hass.services.async_call(
                "notify",
                "send_message",
                {
                    "entity_id": entity_id,
                    "title": title,
                    "message": message,
                },
                blocking=True,
            )
        except Exception:
            return False

        return True

    async def async_send(
        self,
        channel: str,
        entity_id: str,
        title: str,
        message: str,
        **kwargs: Any,
    ) -> bool:
        """Send a notification through the selected channel."""

        if channel in {"telegram", "vk"}:
            return await self.async_send_notify_entity(
                entity_id,
                title,
                message,
            )

        return False
