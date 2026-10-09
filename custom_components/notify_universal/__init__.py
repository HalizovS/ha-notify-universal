"""Notify Universal integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, Event
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
        parse_mode: str = "html",
        telegram_keyboard: str = "",
        vk_keyboard: Any = None,
    ) -> tuple[bool, str | None, str | None]:
        """Try the primary channel and then the fallback channel."""

        primary_service = services.get(primary_channel)

        if not primary_service:
            return False, None, None

        success = await notifier.async_send(
            primary_channel,
            primary_service,
            title,
            message,
            parse_mode=parse_mode,
            telegram_keyboard=telegram_keyboard,
            vk_keyboard=vk_keyboard,
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
            parse_mode=parse_mode,
            telegram_keyboard=telegram_keyboard,
            vk_keyboard=vk_keyboard,
        )

        if fallback_success:
            return True, fallback_channel, fallback_service

        return False, primary_channel, primary_service

    def get_config() -> dict | None:
        """Return the current integration configuration."""

        ignored_keys = {
            "notifier",
            "storage",
            "queue_task",
            "queue_cancel",
            "internet_listener",
            "setup_queue_tracking",
        }

        entries = [
            value
            for key, value in hass.data[DOMAIN].items()
            if key not in ignored_keys
            and isinstance(value, dict)
            and (
                CONF_PRIMARY_CHANNEL in value
                or CONF_TELEGRAM_SERVICE in value
            )
        ]

        return entries[0] if entries else None

    def internet_is_available() -> bool:
        """Return whether the configured internet sensor is available."""

        config_entry = get_config()

        if not config_entry:
            return False

        sensor = config_entry.get(CONF_INTERNET_SENSOR)

        if not sensor:
            return False

        expected_state = config_entry.get(
            CONF_INTERNET_STATE,
            DEFAULT_INTERNET_STATE,
        )

        state = hass.states.get(sensor)

        return bool(state and state.state == expected_state)

    def set_last_message(
        state: str,
        attributes: dict[str, Any],
    ) -> None:
        """Update the last-message entity using a short state value."""

        hass.states.async_set(
            f"{DOMAIN}.last_message",
            state[:255],
            attributes,
        )

    async def async_process_queue() -> None:
        """Send all queued notifications as one message."""

        if not storage.queue or not internet_is_available():
            return

        config_entry = get_config()

        if not config_entry:
            return

        primary_channel = config_entry.get(
            CONF_PRIMARY_CHANNEL,
            CHANNEL_TELEGRAM,
        )
        fallback_channel = config_entry.get(
            CONF_FALLBACK_CHANNEL,
            CHANNEL_NONE,
        )
        services = {
            CHANNEL_TELEGRAM: config_entry.get(CONF_TELEGRAM_SERVICE),
            CHANNEL_VK: config_entry.get(CONF_VK_SERVICE),
        }

        queued_items = list(storage.queue)
        message_parts = [
            f"{index}. {item.get('message', '')}"
            for index, item in enumerate(queued_items, start=1)
        ]
        combined_message = (
            "📬 <b>Доставлено из очереди</b>\n\n"
            + "\n\n".join(message_parts)
        )

        success, used_channel, used_service = await async_send_message(
            "",
            combined_message,
            primary_channel,
            fallback_channel,
            services,
            parse_mode="html",
        )

        if not success:
            schedule_queue_retry()
            return

        await storage.async_clear()

        set_last_message(
            "Уведомления из очереди доставлены",
            {
                "title": "📬 Доставлено из очереди",
                "message": combined_message,
                "primary_channel": primary_channel,
                "primary_service": services.get(primary_channel),
                "fallback_channel": fallback_channel,
                "used_channel": used_channel,
                "used_service": used_service,
                "success": True,
                "queued": False,
                "queue_size": storage.size,
                "from_queue": True,
                "queue_messages": len(queued_items),
            },
        )

    async def async_start_queue_processing() -> None:
        """Start queue processing without duplicate concurrent runs."""

        if hass.data[DOMAIN]["queue_task"] is not None:
            return

        task = hass.async_create_task(async_process_queue())
        hass.data[DOMAIN]["queue_task"] = task

        try:
            await task
        finally:
            if hass.data[DOMAIN].get("queue_task") is task:
                hass.data[DOMAIN]["queue_task"] = None

    def start_queue_processing() -> None:
        """Start queue processing safely from a timer callback."""

        hass.add_job(async_start_queue_processing)

    def cancel_stabilization() -> None:
        """Cancel the queue processing timer."""

        cancel = hass.data[DOMAIN].get("queue_cancel")

        if cancel:
            cancel()
            hass.data[DOMAIN]["queue_cancel"] = None

    def start_stabilization() -> None:
        """Start the internet stabilization timer."""

        cancel_stabilization()

        if not storage.queue:
            return

        config_entry = get_config()

        if not config_entry:
            return

        if not config_entry.get(
            CONF_QUEUE_ENABLED,
            DEFAULT_QUEUE_ENABLED,
        ):
            return

        if not config_entry.get(CONF_INTERNET_SENSOR):
            return

        if not internet_is_available():
            return

        hass.data[DOMAIN]["queue_cancel"] = async_call_later(
            hass,
            timedelta(seconds=DEFAULT_INTERNET_STABILIZATION),
            lambda _: start_queue_processing(),
        )

    def schedule_queue_retry() -> None:
        """Retry queue delivery after the stabilization interval."""

        if not storage.queue:
            return

        config_entry = get_config()

        if not config_entry:
            return

        if not config_entry.get(
            CONF_QUEUE_ENABLED,
            DEFAULT_QUEUE_ENABLED,
        ):
            return

        if not internet_is_available():
            return

        cancel_stabilization()

        hass.data[DOMAIN]["queue_cancel"] = async_call_later(
            hass,
            timedelta(seconds=DEFAULT_INTERNET_STABILIZATION),
            lambda _: start_queue_processing(),
        )

    async def async_internet_state_changed(event: Event) -> None:
        """Handle changes to the configured internet sensor."""

        new_state = event.data.get("new_state")

        if not new_state:
            return

        config_entry = get_config()

        if not config_entry:
            return

        expected_state = config_entry.get(
            CONF_INTERNET_STATE,
            DEFAULT_INTERNET_STATE,
        )

        if new_state.state == expected_state:
            start_stabilization()
        else:
            cancel_stabilization()

    def setup_queue_tracking() -> None:
        """Set up the internet sensor listener."""

        old_listener = hass.data[DOMAIN].pop("internet_listener", None)

        if old_listener:
            old_listener()

        cancel_stabilization()

        config_entry = get_config()

        if not config_entry:
            return

        if not config_entry.get(
            CONF_QUEUE_ENABLED,
            DEFAULT_QUEUE_ENABLED,
        ):
            return

        sensor = config_entry.get(CONF_INTERNET_SENSOR)

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

    hass.data[DOMAIN]["setup_queue_tracking"] = setup_queue_tracking

    async def async_handle_send(call: ServiceCall) -> None:
        """Handle the notify_universal.send service."""

        title = call.data.get("title", "")
        message = call.data.get("message", "")
        parse_mode = call.data.get("parse_mode", "html")
        telegram_keyboard = call.data.get("telegram_keyboard", "")
        vk_keyboard = call.data.get("vk_keyboard")

        config_entry = get_config()

        if not config_entry:
            return

        primary_channel = config_entry.get(
            CONF_PRIMARY_CHANNEL,
            CHANNEL_TELEGRAM,
        )
        fallback_channel = config_entry.get(
            CONF_FALLBACK_CHANNEL,
            CHANNEL_NONE,
        )
        services = {
            CHANNEL_TELEGRAM: config_entry.get(CONF_TELEGRAM_SERVICE),
            CHANNEL_VK: config_entry.get(CONF_VK_SERVICE),
        }
        queue_enabled = config_entry.get(
            CONF_QUEUE_ENABLED,
            DEFAULT_QUEUE_ENABLED,
        )

        if queue_enabled and not internet_is_available():
            await storage.async_add(title, message)

            set_last_message(
                message or title or "Уведомление поставлено в очередь",
                {
                    "title": title,
                    "message": message,
                    "primary_channel": primary_channel,
                    "primary_service": services.get(primary_channel),
                    "fallback_channel": fallback_channel,
                    "used_channel": None,
                    "used_service": None,
                    "success": False,
                    "queued": True,
                    "queue_size": storage.size,
                    "from_queue": False,
                    "reason": "internet_unavailable",
                },
            )
            return

        success, used_channel, used_service = await async_send_message(
            title,
            message,
            primary_channel,
            fallback_channel,
            services,
            parse_mode=parse_mode,
            telegram_keyboard=telegram_keyboard,
            vk_keyboard=vk_keyboard,
        )

        if not success and queue_enabled:
            await storage.async_add(title, message)
            schedule_queue_retry()

        set_last_message(
            message or title or "Уведомление обработано",
            {
                "title": title,
                "message": message,
                "primary_channel": primary_channel,
                "primary_service": services.get(primary_channel),
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

    setup_queue_tracking = hass.data[DOMAIN].get("setup_queue_tracking")

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

    setup_queue_tracking = hass.data[DOMAIN].get("setup_queue_tracking")

    if setup_queue_tracking:
        setup_queue_tracking()

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Unload Notify Universal."""

    cancel = hass.data[DOMAIN].pop("queue_cancel", None)

    if cancel:
        cancel()

    listener = hass.data[DOMAIN].pop("internet_listener", None)

    if listener:
        listener()

    task = hass.data[DOMAIN].pop("queue_task", None)

    if task:
        task.cancel()

    hass.data[DOMAIN].pop("setup_queue_tracking", None)
    hass.data[DOMAIN].pop(entry.entry_id, None)

    return True
