"""Constants for the Ovum Mira custom integration."""

from datetime import timedelta
from typing import Final

DOMAIN: Final[str] = "ovum_mira"
SCAN_INTERVAL: Final[timedelta] = timedelta(seconds=15)

CONF_WPM_UNIT_ID: Final[str] = "wpm_unit_id"
CONF_LICENSE_LEVEL: Final[str] = "license_level"
