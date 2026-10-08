"""Notification delivery for Notify Universal."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant


class NotifyUniversalNotifier:
    """Handle notification delivery."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the notifier."""

        self.hass = hass

    async def async_send_telegram(
        self,
        service: str,
        title: str,
        message: str,
    ) -> bool:
        """Send a notification through Telegram."""

        try:
            await self.hass.services.async_call(
                "telegram_bot",
                "send_message",
                {
                    "entity_id": [f"notify.{service}"],
                    "title": title,
                    "message": message,
                },
                blocking=True,
            )
        except Exception:
            return False

        return True

    async def async_send_vk(
        self,
        service: str,
        title: str,
        message: str,
    ) -> bool:
        """Send a notification through VK."""

        try:
            await self.hass.services.async_call(
                "notify",
                service,
                {
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
        service: str,
        title: str,
        message: str,
        **kwargs: Any,
    ) -> bool:
        """Send a notification through the selected channel."""

        if channel == "telegram":
            return await self.async_send_telegram(
                service,
                title,
                message,
            )

        if channel == "vk":
            return await self.async_send_vk(
                service,
                title,
                message,
            )

        return False
