"""Config flow for Notify Universal."""

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback

from .const import (
    CHANNEL_NONE,
    CHANNEL_TELEGRAM,
    CHANNEL_VK,
    CONF_FALLBACK_CHANNEL,
    CONF_PRIMARY_CHANNEL,
    CONF_TELEGRAM_SERVICE,
    CONF_VK_SERVICE,
    DOMAIN,
    NAME,
)


def _get_notify_entities(hass: HomeAssistant) -> list[str]:
    """Return all available notify entities."""
    return sorted(
        state.entity_id
        for state in hass.states.async_all()
        if state.entity_id.startswith("notify.")
    )


def _get_telegram_entities(hass: HomeAssistant) -> list[str]:
    """Return available Telegram notify entities."""
    return [
        entity
        for entity in _get_notify_entities(hass)
        if entity.startswith("notify.telegram_")
    ]


def _get_vk_entities(hass: HomeAssistant) -> list[str]:
    """Return available VK notify entities."""
    return [
        entity
        for entity in _get_notify_entities(hass)
        if entity == "notify.vk"
    ]


class NotifyUniversalConfigFlow(
    config_entries.ConfigFlow,
    domain=DOMAIN,
):
    """Handle a config flow for Notify Universal."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial setup step."""

        telegram_entities = _get_telegram_entities(self.hass)
        vk_entities = _get_vk_entities(self.hass)

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
                    CONF_TELEGRAM_SERVICE,
                ): vol.In(
                    {
                        entity: entity
                        for entity in telegram_entities
                    }
                ),
                vol.Required(
                    CONF_VK_SERVICE,
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

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""

        return NotifyUniversalOptionsFlow()


class NotifyUniversalOptionsFlow(config_entries.OptionsFlow):
    """Handle Notify Universal options."""

    async def async_step_init(self, user_input=None):
        """Handle the options flow."""

        telegram_entities = _get_telegram_entities(self.hass)
        vk_entities = _get_vk_entities(self.hass)

        current = {
            **self.config_entry.data,
            **self.config_entry.options,
        }

        if user_input is not None:
            return self.async_create_entry(
                data=user_input,
            )

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_PRIMARY_CHANNEL,
                    default=current.get(
                        CONF_PRIMARY_CHANNEL,
                        CHANNEL_TELEGRAM,
                    ),
                ): vol.In(
                    {
                        CHANNEL_TELEGRAM: "Telegram",
                        CHANNEL_VK: "VK",
                    }
                ),
                vol.Required(
                    CONF_TELEGRAM_SERVICE,
                    default=current.get(
                        CONF_TELEGRAM_SERVICE,
                        telegram_entities[0]
                        if telegram_entities
                        else "",
                    ),
                ): vol.In(
                    {
                        entity: entity
                        for entity in telegram_entities
                    }
                ),
                vol.Required(
                    CONF_VK_SERVICE,
                    default=current.get(
                        CONF_VK_SERVICE,
                        vk_entities[0]
                        if vk_entities
                        else "",
                    ),
                ): vol.In(
                    {
                        entity: entity
                        for entity in vk_entities
                    }
                ),
                vol.Optional(
                    CONF_FALLBACK_CHANNEL,
                    default=current.get(
                        CONF_FALLBACK_CHANNEL,
                        CHANNEL_VK,
                    ),
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
            step_id="init",
            data_schema=schema,
        )
