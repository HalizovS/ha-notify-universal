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

CONF_TELEGRAM_SERVICE = "telegram_service"
CONF_VK_SERVICE = "vk_service"


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

        config_entry_data = entries[0]

        primary_channel = config_entry_data.get(
            CONF_PRIMARY_CHANNEL,
            CHANNEL_TELEGRAM,
        )

        fallback_channel = config_entry_data.get(
            CONF_FALLBACK_CHANNEL,
            CHANNEL_NONE,
        )

        telegram_service = config_entry_data.get(
            CONF_TELEGRAM_SERVICE,
        )

        vk_service = config_entry_data.get(
            CONF_VK_SERVICE,
        )

        services = {
            CHANNEL_TELEGRAM: telegram_service,
            CHANNEL_VK: vk_service,
        }

        primary_service = services.get(primary_channel)

        if not primary_service:
            return

        success = await notifier.async_send(
            primary_channel,
            primary_service,
            title,
            message,
        )

        used_channel = primary_channel
        used_service = primary_service

        if not success and fallback_channel != CHANNEL_NONE:
            fallback_service = services.get(fallback_channel)

            if fallback_service:
                fallback_success = await notifier.async_send(
                    fallback_channel,
                    fallback_service,
                    title,
                    message,
                )

                if fallback_success:
                    success = True
                    used_channel = fallback_channel
                    used_service = fallback_service

        hass.states.async_set(
            f"{DOMAIN}.last_message",
            message,
            {
                "title": title,
                "primary_channel": primary_channel,
                "primary_service": primary_service,
                "fallback_channel": fallback_channel,
                "used_channel": used_channel,
                "used_service": used_service,
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

    hass.data[DOMAIN][entry.entry_id] = {
        **entry.data,
        **entry.options,
    }

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Unload Notify Universal."""

    hass.data[DOMAIN].pop(entry.entry_id, None)

    return True
