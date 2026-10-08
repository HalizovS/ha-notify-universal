"""Config flow for Notify Universal."""

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME

from .const import (
    CHANNEL_NONE,
    CHANNEL_TELEGRAM,
    CHANNEL_VK,
    CONF_FALLBACK_CHANNEL,
    CONF_PRIMARY_CHANNEL,
    DOMAIN,
    NAME,
)


class NotifyUniversalConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Notify Universal."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial setup step."""

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
