"""Constants for the X-Sense Home Security integration."""

import logging

DOMAIN = "xsense"
MANUFACTURER = "X-Sense"
COORDINATOR = "coordinator"

DEFAULT_SCAN_INTERVAL = 300
CAMERA_SCAN_INTERVAL = 1800
CAMERA_AI_HISTORY_SCAN_INTERVAL = 60
CAMERA_AI_SERVICE_AVAILABLE = "cameraAiServiceAvailable"
POLL_INTERVAL_MIN = 5

CONF_RECORDING_MEDIA_SYNC_ENABLED = "recording_media_sync_enabled"
CONF_RECORDING_MEDIA_SYNC_HOURS = "recording_media_sync_hours"
CONF_RECORDING_MEDIA_STORAGE_PATH = "recording_media_storage_path"
CONF_RECORDING_MEDIA_DAYS_ORDER = "recording_media_days_order"
CONF_RECORDING_MEDIA_CLIPS_ORDER = "recording_media_clips_order"
CONF_RECORDING_NOTIFICATION_QUALITY = "recording_notification_quality"
DEFAULT_RECORDING_MEDIA_SYNC_ENABLED = False
DEFAULT_RECORDING_MEDIA_SYNC_HOURS = 24
DEFAULT_RECORDING_MEDIA_STORAGE_PATH = "/media/xsense_recordings"
DEFAULT_RECORDING_MEDIA_DAYS_ORDER = "Descending"
DEFAULT_RECORDING_MEDIA_CLIPS_ORDER = "Descending"
DEFAULT_RECORDING_NOTIFICATION_QUALITY = "HD"
RECORDING_MEDIA_ORDER_OPTIONS = ["Ascending", "Descending"]
RECORDING_NOTIFICATION_QUALITY_OPTIONS = ["HD", "SD"]

LOGGER = logging.getLogger(__package__)

STATE_SIGNAL = [
    "no_signal",
    "weak",
    "moderate",
    "good",
]

# Raw protocol metadata belongs in downloadable diagnostics, not on device pages.
NON_ENTITY_DIAGNOSTIC_SENSOR_KEYS = frozenset(
    {
        "alarm_occur",
        "alarm_source",
        "camera_activated_time",
        "camera_dormancy_message",
        "camera_dormancy_wake_time",
        "camera_firmware_status",
        "camera_firmware_version",
        "camera_network_name",
        "camera_offline_time",
        "camera_status_code",
        "camera_thumbnail_time",
        "camera_time_zone_area",
        "camera_wifi_channel",
        "camera_wired_mac_address",
        "category",
        "check_type",
        "color",
        "device_type",
        "ip",
        "light_event",
        "location",
        "long_warning",
        "pir_interval",
        "pir_sensitivity",
        "re_alarm",
        "reported_device_type",
        "safe_mode",
        "short_warning",
        "smoke_edition",
        "standard",
        "test_time",
        "time",
        "timezone",
        "utc_time",
        "wifi_rssi_level",
        "wifi_ssid",
        "wifi_sw",
        "zone_name",
    }
)

NON_ENTITY_DIAGNOSTIC_BINARY_SENSOR_KEYS = frozenset(
    {
        "alarm_sound_enabled",
        "app_tip_enabled",
        "schedule_tip_enabled",
        "test_active",
        "timezone_enabled",
        "timezone_valid",
    }
)
