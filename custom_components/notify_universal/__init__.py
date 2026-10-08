"""Notify Universal integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall

from .const import (
    CHANNEL_NONE,
    CHANNEL_TELEGRAM,
    CHANNEL_VK,
    CONF_FALLBACK_CHANNEL,
    CONF_PRIMARY_CHANNEL,
    DOMAIN,
)
from .notifier import NotifyUniversalNotifier


SERVICE_SEND = "send"


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Notify Universal integration."""

    notifier = NotifyUniversalNotifier(hass)
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["notifier"] = notifier

    async def async_handle_send(call: ServiceCall) -> None:
        """Handle the notify_universal.send service."""

        title = call.data.get("title", "")
        message = call.data.get("message", "")

        entries = [
            value
            for key, value in hass.data[DOMAIN].items()
            if key != "notifier"
        ]

        if not entries:
            return

        config = entries[0]

        primary_channel = config.get(
            CONF_PRIMARY_CHANNEL,
            CHANNEL_TELEGRAM,
        )
        fallback_channel = config.get(
            CONF_FALLBACK_CHANNEL,
            CHANNEL_NONE,
        )

        success = await notifier.async_send(
            primary_channel,
            title,
            message,
        )

        if not success and fallback_channel != CHANNEL_NONE:
            await notifier.async_send(
                fallback_channel,
                title,
                message,
            )

        hass.states.async_set(
            f"{DOMAIN}.last_message",
            message,
            {
                "title": title,
                "primary_channel": primary_channel,
                "fallback_channel": fallback_channel,
                "success": success,
            },
        )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SEND,
        async_handle_send,
    )

    return True


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Set up Notify Universal from a config entry."""

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Unload Notify Universal."""

    hass.data[DOMAIN].pop(entry.entry_id, None)

    return True
