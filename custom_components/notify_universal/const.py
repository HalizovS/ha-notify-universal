"""Constants for Notify Universal."""

DOMAIN = "notify_universal"
NAME = "Notify Universal"

CONF_PRIMARY_CHANNEL = "primary_channel"
CONF_FALLBACK_CHANNEL = "fallback_channel"
CONF_TELEGRAM_SERVICE = "telegram_service"
CONF_VK_SERVICE = "vk_service"

CONF_QUEUE_ENABLED = "queue_enabled"
CONF_INTERNET_SENSOR = "internet_sensor"
CONF_INTERNET_STATE = "internet_state"

DEFAULT_QUEUE_ENABLED = False
DEFAULT_INTERNET_STABILIZATION = 180
DEFAULT_INTERNET_STATE = "on"

CHANNEL_TELEGRAM = "telegram"
CHANNEL_VK = "vk"
CHANNEL_NONE = "none"
