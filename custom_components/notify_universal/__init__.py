"""Notify Universal integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall

from .const import DOMAIN


SERVICE_SEND = "send"


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Notify Universal integration."""

    async def async_handle_send(call: ServiceCall) -> None:
        """Handle the notify_universal.send service."""

        title = call.data.get("title", "")
        message = call.data.get("message", "")

        hass.states.async_set(
            f"{DOMAIN}.last_message",
            message,
            {
                "title": title,
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
