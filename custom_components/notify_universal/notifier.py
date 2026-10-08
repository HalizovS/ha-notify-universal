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
        parse_mode: str = "html",
        telegram_keyboard: str = "",
        vk_keyboard: Any = None,
    ) -> bool:
        """Send a notification through a notify entity."""

        data: dict[str, Any] = {
            "entity_id": entity_id,
            "title": title,
            "message": message,
            "parse_mode": parse_mode,
        }

        if telegram_keyboard:
            data["inline_keyboard"] = telegram_keyboard

        if vk_keyboard is not None:
            data["keyboard"] = vk_keyboard
            data["inline_keyboard"] = True

        try:
            await self.hass.services.async_call(
                "notify",
                "send_message",
                data,
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

        if channel not in {"telegram", "vk"}:
            return False

        return await self.async_send_notify_entity(
            entity_id=entity_id,
            title=title,
            message=message,
            parse_mode=kwargs.get(
                "parse_mode",
                "html",
            ),
            telegram_keyboard=kwargs.get(
                "telegram_keyboard",
                "",
            ),
            vk_keyboard=kwargs.get(
                "vk_keyboard",
            ),
        )
