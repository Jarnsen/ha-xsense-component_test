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
