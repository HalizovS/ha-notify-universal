"""Config flow for Notify Universal."""

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant

from .const import (
    CHANNEL_NONE,
    CHANNEL_TELEGRAM,
    CHANNEL_VK,
    CONF_FALLBACK_CHANNEL,
    CONF_PRIMARY_CHANNEL,
    DOMAIN,
    NAME,
)


def _get_notify_services(hass: HomeAssistant) -> list[str]:
    """Return available notify services."""
    services = hass.services.async_services().get("notify", {})
    return sorted(services)


class NotifyUniversalConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Notify Universal."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial setup step."""

        telegram_services = [
            service
            for service in _get_notify_services(self.hass)
            if "telegram" in service.lower()
        ]

        vk_services = [
            service
            for service in _get_notify_services(self.hass)
            if service.lower() == "vk"
        ]

        if user_input is not None:
            return self.async_create_entry(
                title=NAME,
                data=user_input,
            )

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_PRIMARY_CHANNEL,
                    default=CHANNEL_TELEGRAM,
                ): vol.In(
                    {
                        CHANNEL_TELEGRAM: "Telegram",
                        CHANNEL_VK: "VK",
                    }
                ),
                vol.Required(
                    "telegram_service",
                ): vol.In(
                    {
                        service: service
                        for service in telegram_services
                    }
                ),
                vol.Required(
                    "vk_service",
                ): vol.In(
                    {
                        service: service
                        for service in vk_services
                    }
                ),
                vol.Optional(
                    CONF_FALLBACK_CHANNEL,
                    default=CHANNEL_VK,
                ): vol.In(
                    {
                        CHANNEL_TELEGRAM: "Telegram",
                        CHANNEL_VK: "VK",
                        CHANNEL_NONE: "Не использовать",
                    }
                ),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
        )
