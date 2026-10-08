"""Config flow for Notify Universal."""

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.selector import EntitySelector

from .const import (
    CHANNEL_NONE,
    CHANNEL_TELEGRAM,
    CHANNEL_VK,
    CONF_FALLBACK_CHANNEL,
    CONF_INTERNET_SENSOR,
    CONF_INTERNET_STATE,
    CONF_PRIMARY_CHANNEL,
    CONF_QUEUE_ENABLED,
    CONF_TELEGRAM_SERVICE,
    CONF_VK_SERVICE,
    DEFAULT_INTERNET_STATE,
    DEFAULT_QUEUE_ENABLED,
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

    async def async_step_user(
        self,
        user_input=None,
    ):
        """Handle the initial setup step."""

        telegram_entities = _get_telegram_entities(self.hass)
        vk_entities = _get_vk_entities(self.hass)

        if user_input is not None:
            if user_input.get(
                CONF_QUEUE_ENABLED,
                DEFAULT_QUEUE_ENABLED,
            ):
                self._data = user_input
                return await self.async_step_queue()

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
                vol.Optional(
                    CONF_QUEUE_ENABLED,
                    default=DEFAULT_QUEUE_ENABLED,
                ): bool,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
        )

    async def async_step_queue(
        self,
        user_input=None,
    ):
        """Handle queue settings."""

        if user_input is not None:
            data = {
                **self._data,
                **user_input,
            }

            return self.async_create_entry(
                title=NAME,
                data=data,
            )

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_INTERNET_SENSOR,
                ): EntitySelector(),
                vol.Required(
                    CONF_INTERNET_STATE,
                    default=DEFAULT_INTERNET_STATE,
                ): str,
            }
        )

        return self.async_show_form(
            step_id="queue",
            data_schema=schema,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""

        return NotifyUniversalOptionsFlow()


class NotifyUniversalOptionsFlow(
    config_entries.OptionsFlow
):
    """Handle Notify Universal options."""

    def __init__(self) -> None:
        """Initialize options flow."""

        self._data: dict = {}

    async def async_step_init(
        self,
        user_input=None,
    ):
        """Handle the main options step."""

        telegram_entities = _get_telegram_entities(self.hass)
        vk_entities = _get_vk_entities(self.hass)

        current = {
            **self.config_entry.data,
            **self.config_entry.options,
        }

        if user_input is not None:
            if user_input.get(
                CONF_QUEUE_ENABLED,
                DEFAULT_QUEUE_ENABLED,
            ):
                self._data = {
                    **current,
                    **user_input,
                }

                return await self.async_step_queue()

            data = {
                **user_input,
            }

            data.pop(
                CONF_INTERNET_SENSOR,
                None,
            )
            data.pop(
                CONF_INTERNET_STATE,
                None,
            )

            return self.async_create_entry(
                data=data,
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
                vol.Optional(
                    CONF_QUEUE_ENABLED,
                    default=current.get(
                        CONF_QUEUE_ENABLED,
                        DEFAULT_QUEUE_ENABLED,
                    ),
                ): bool,
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
        )

    async def async_step_queue(
        self,
        user_input=None,
    ):
        """Handle queue settings."""

        current = {
            **self.config_entry.data,
            **self.config_entry.options,
            **self._data,
        }

        if user_input is not None:
            data = {
                **self._data,
                **user_input,
            }

            return self.async_create_entry(
                data=data,
            )

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_INTERNET_SENSOR,
                    default=current.get(
                        CONF_INTERNET_SENSOR,
                    ),
                ): EntitySelector(),
                vol.Required(
                    CONF_INTERNET_STATE,
                    default=current.get(
                        CONF_INTERNET_STATE,
                        DEFAULT_INTERNET_STATE,
                    ),
                ): str,
            }
        )

        return self.async_show_form(
            step_id="queue",
            data_schema=schema,
        )
