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

LOGGER = logging.getLogger(__package__)

STATE_SIGNAL = [
    "no_signal",
    "weak",
    "moderate",
    "good",
]
