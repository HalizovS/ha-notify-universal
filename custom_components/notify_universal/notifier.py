"""Notification delivery for Notify Universal."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant


_LOGGER = logging.getLogger(__name__)


class NotifyUniversalNotifier:
    """Handle notification delivery."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the notifier."""

        self.hass = hass

    async def async_send_telegram(
        self,
        entity_id: str,
        title: str,
        message: str,
        parse_mode: str = "html",
        telegram_keyboard: str = "",
    ) -> bool:
        """Send a notification through Telegram."""

        data: dict[str, Any] = {
            "entity_id": [entity_id],
            "title": title,
            "message": message,
            "parse_mode": parse_mode,
        }

        if telegram_keyboard:
            data["inline_keyboard"] = [
                telegram_keyboard,
            ]

        try:
            await self.hass.services.async_call(
                "telegram_bot",
                "send_message",
                data,
                blocking=True,
            )
        except Exception:
            _LOGGER.exception(
                "Failed to send Telegram notification through %s",
                entity_id,
            )
            return False

        return True

    async def async_send_vk(
        self,
        entity_id: str,
        title: str,
        message: str,
        parse_mode: str = "html",
        vk_keyboard: Any = None,
    ) -> bool:
        """Send a notification through VK."""

        data: dict[str, Any] = {
            "parse_mode": parse_mode,
            "disable_mentions": False,
            "inline_keyboard": True,
            "auto_answer_callback": False,
            "timeout": 60,
            "title": title,
            "message": message,
        }

        if vk_keyboard is not None:
            data["keyboard"] = vk_keyboard

        try:
            await self.hass.services.async_call(
                "vk_notify",
                "send_message",
                data,
                target={
                    "entity_id": entity_id,
                },
                blocking=True,
            )
        except Exception:
            _LOGGER.exception(
                "Failed to send VK notification through %s",
                entity_id,
            )
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

        if channel == "telegram":
            return await self.async_send_telegram(
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
            )

        if channel == "vk":
            return await self.async_send_vk(
                entity_id=entity_id,
                title=title,
                message=message,
                parse_mode=kwargs.get(
                    "parse_mode",
                    "html",
                ),
                vk_keyboard=kwargs.get(
                    "vk_keyboard",
                ),
            )

        _LOGGER.error(
            "Unsupported notification channel: %s",
            channel,
        )
        return False
