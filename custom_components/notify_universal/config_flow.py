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


def _get_notify_entities(hass: HomeAssistant) -> list[str]:
    """Return available notify entities."""
    return sorted(
        state.entity_id
        for state in hass.states.async_all("notify")
    )


class NotifyUniversalConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Notify Universal."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial setup step."""

        notify_entities = _get_notify_entities(self.hass)

        telegram_entities = [
            entity
            for entity in notify_entities
            if "telegram" in entity.lower()
        ]

        vk_entities = [
            entity
            for entity in notify_entities
            if "vk" in entity.lower()
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
                        entity: entity
                        for entity in telegram_entities
                    }
                ),
                vol.Required(
                    "vk_service",
                ): vol.In(
                    {
                        entity: entity
                        for entity in vk_entities
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
