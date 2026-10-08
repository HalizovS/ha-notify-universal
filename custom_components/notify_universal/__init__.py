"""Notify Universal integration."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers.event import (
    async_call_later,
    async_track_state_change_event,
)

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
    DEFAULT_INTERNET_STABILIZATION,
    DEFAULT_INTERNET_STATE,
    DEFAULT_QUEUE_ENABLED,
    DOMAIN,
)
from .notifier import NotifyUniversalNotifier
from .storage import NotifyUniversalStorage


SERVICE_SEND = "send"


async def async_setup(
    hass: HomeAssistant,
    config: dict,
) -> bool:
    """Set up the Notify Universal integration."""

    notifier = NotifyUniversalNotifier(hass)
    storage = NotifyUniversalStorage(hass)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["notifier"] = notifier
    hass.data[DOMAIN]["storage"] = storage
    hass.data[DOMAIN]["queue_task"] = None
    hass.data[DOMAIN]["queue_cancel"] = None
    hass.data[DOMAIN]["internet_listener"] = None

    await storage.async_load()

    async def async_send_message(
        title: str,
        message: str,
        primary_channel: str,
        fallback_channel: str,
        services: dict[str, str | None],
    ) -> tuple[bool, str | None, str | None]:
        """Try to send a notification."""

        primary_service = services.get(primary_channel)

        if not primary_service:
            return False, None, None

        success = await notifier.async_send(
            primary_channel,
            primary_service,
            title,
            message,
        )

        if success:
            return True, primary_channel, primary_service

        if fallback_channel == CHANNEL_NONE:
            return False, primary_channel, primary_service

        fallback_service = services.get(fallback_channel)

        if not fallback_service:
            return False, primary_channel, primary_service

        fallback_success = await notifier.async_send(
            fallback_channel,
            fallback_service,
            title,
            message,
        )

        if fallback_success:
            return True, fallback_channel, fallback_service

        return False, primary_channel, primary_service

    def get_config() -> dict | None:
        """Return the current integration configuration."""

        entries = [
            value
            for key, value in hass.data[DOMAIN].items()
            if key not in {
                "notifier",
                "storage",
                "queue_task",
                "queue_cancel",
                "internet_listener",
                "setup_queue_tracking",
            }
        ]

        if not entries:
            return None

        return entries[0]

    def internet_is_available() -> bool:
        """Return whether the configured internet sensor is available."""

        config = get_config()

        if not config:
            return False

        sensor = config.get(CONF_INTERNET_SENSOR)

        if not sensor:
            return False

        expected_state = config.get(
            CONF_INTERNET_STATE,
            DEFAULT_INTERNET_STATE,
        )

        state = hass.states.get(sensor)

        return bool(
            state
            and state.state == expected_state
        )

    async def async_process_queue() -> None:
        """Process all queued notifications."""

        while storage.queue:
            if not internet_is_available():
                return

            config = get_config()

            if not config:
                return

            primary_channel = config.get(
                CONF_PRIMARY_CHANNEL,
                CHANNEL_TELEGRAM,
            )

            fallback_channel = config.get(
                CONF_FALLBACK_CHANNEL,
                CHANNEL_NONE,
            )

            services = {
                CHANNEL_TELEGRAM: config.get(
                    CONF_TELEGRAM_SERVICE,
                ),
                CHANNEL_VK: config.get(
                    CONF_VK_SERVICE,
                ),
            }

            item = storage.queue[0]

            success, used_channel, used_service = (
                await async_send_message(
                    item.get("title", ""),
                    item.get("message", ""),
                    primary_channel,
                    fallback_channel,
                    services,
                )
            )

            if not success:
                return

            await storage.async_remove_first()

            hass.states.async_set(
                f"{DOMAIN}.last_message",
                item.get("message", ""),
                {
                    "title": item.get("title", ""),
                    "primary_channel": primary_channel,
                    "primary_service": services.get(
                        primary_channel,
                    ),
                    "fallback_channel": fallback_channel,
                    "used_channel": used_channel,
                    "used_service": used_service,
                    "success": True,
                    "queued": False,
                    "queue_size": storage.size,
                    "from_queue": True,
                },
            )

    async def async_start_queue_processing() -> None:
        """Start processing the queue."""

        if hass.data[DOMAIN]["queue_task"] is not None:
            return

        hass.data[DOMAIN]["queue_task"] = hass.async_create_task(
            async_process_queue()
        )

        try:
            await hass.data[DOMAIN]["queue_task"]
        finally:
            hass.data[DOMAIN]["queue_task"] = None

    @callback
    def cancel_stabilization() -> None:
        """Cancel the internet stabilization timer."""

        cancel = hass.data[DOMAIN].get("queue_cancel")

        if cancel:
            cancel()
            hass.data[DOMAIN]["queue_cancel"] = None

    @callback
    def start_stabilization() -> None:
        """Start the internet stabilization timer."""

        cancel_stabilization()

        if not storage.queue:
            return

        config = get_config()

        if not config:
            return

        if not config.get(
            CONF_QUEUE_ENABLED,
            DEFAULT_QUEUE_ENABLED,
        ):
            return

        sensor = config.get(CONF_INTERNET_SENSOR)

        if not sensor:
            return

        if not internet_is_available():
            return

        hass.data[DOMAIN]["queue_cancel"] = async_call_later(
            hass,
            timedelta(
                seconds=DEFAULT_INTERNET_STABILIZATION
            ),
            lambda _: hass.async_create_task(
                async_start_queue_processing()
            ),
        )

    @callback
    def async_internet_state_changed(event) -> None:
        """Handle internet sensor state changes."""

        new_state = event.data.get("new_state")

        if not new_state:
            return

        config = get_config()

        if not config:
            return

        expected_state = config.get(
            CONF_INTERNET_STATE,
            DEFAULT_INTERNET_STATE,
        )

        if new_state.state == expected_state:
            start_stabilization()
        else:
            cancel_stabilization()

    def setup_queue_tracking() -> None:
        """Set up tracking for the configured internet sensor."""

        old_listener = hass.data[DOMAIN].pop(
            "internet_listener",
            None,
        )

        if old_listener:
            old_listener()

        cancel_stabilization()

        config = get_config()

        if not config:
            return

        if not config.get(
            CONF_QUEUE_ENABLED,
            DEFAULT_QUEUE_ENABLED,
        ):
            return

        sensor = config.get(CONF_INTERNET_SENSOR)

        if not sensor:
            return

        hass.data[DOMAIN]["internet_listener"] = (
            async_track_state_change_event(
                hass,
                [sensor],
                async_internet_state_changed,
            )
        )

        start_stabilization()

    hass.data[DOMAIN]["setup_queue_tracking"] = (
        setup_queue_tracking
    )

    async def async_handle_send(call: ServiceCall) -> None:
        """Handle the notify_universal.send service."""

        title = call.data.get("title", "")
        message = call.data.get("message", "")

        config = get_config()

        if not config:
            return

        primary_channel = config.get(
            CONF_PRIMARY_CHANNEL,
            CHANNEL_TELEGRAM,
        )

        fallback_channel = config.get(
            CONF_FALLBACK_CHANNEL,
            CHANNEL_NONE,
        )

        services = {
            CHANNEL_TELEGRAM: config.get(
                CONF_TELEGRAM_SERVICE,
            ),
            CHANNEL_VK: config.get(
                CONF_VK_SERVICE,
            ),
        }

        success, used_channel, used_service = (
            await async_send_message(
                title,
                message,
                primary_channel,
                fallback_channel,
                services,
            )
        )

        queue_enabled = config.get(
            CONF_QUEUE_ENABLED,
            DEFAULT_QUEUE_ENABLED,
        )

        if not success and queue_enabled:
            await storage.async_add(
                title,
                message,
            )

        hass.states.async_set(
            f"{DOMAIN}.last_message",
            message,
            {
                "title": title,
                "primary_channel": primary_channel,
                "primary_service": services.get(
                    primary_channel,
                ),
                "fallback_channel": fallback_channel,
                "used_channel": used_channel,
                "used_service": used_service,
                "success": success,
                "queued": not success and queue_enabled,
                "queue_size": storage.size,
                "from_queue": False,
            },
        )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SEND,
        async_handle_send,
    )

    return True


async def async_update_listener(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> None:
    """Update Notify Universal after options change."""

    hass.data[DOMAIN][entry.entry_id] = {
        **entry.data,
        **entry.options,
    }

    setup_queue_tracking = hass.data[DOMAIN].get(
        "setup_queue_tracking"
    )

    if setup_queue_tracking:
        setup_queue_tracking()


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

    entry.async_on_unload(
        entry.add_update_listener(async_update_listener)
    )

    setup_queue_tracking = hass.data[DOMAIN].get(
        "setup_queue_tracking"
    )

    if setup_queue_tracking:
        setup_queue_tracking()

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Unload Notify Universal."""

    cancel = hass.data[DOMAIN].pop(
        "queue_cancel",
        None,
    )

    if cancel:
        cancel()

    listener = hass.data[DOMAIN].pop(
        "internet_listener",
        None,
    )

    if listener:
        listener()

    task = hass.data[DOMAIN].pop(
        "queue_task",
        None,
    )

    if task:
        task.cancel()

    hass.data[DOMAIN].pop(
        "setup_queue_tracking",
        None,
    )

    hass.data[DOMAIN].pop(
        entry.entry_id,
        None,
    )

    return True
