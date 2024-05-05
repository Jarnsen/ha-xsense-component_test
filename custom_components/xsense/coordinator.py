"""DataUpdateCoordinator for the XSense integration."""
from __future__ import annotations

from contextlib import suppress
from datetime import timedelta
from typing import Any

from xsense import AsyncXSense
from xsense.exceptions import APIFailure, AuthFailed, NotFoundError, SessionExpired

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN, LOGGER


class XSenseDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """A XSense Data Update Coordinator."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the XSense hub."""
        LOGGER.debug("XSenseDataUpdateCoordinator:__init__")
        self.entry = entry
        self.xsense: AsyncXSense | None = None
        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
            always_update=True,
        )

    async def _connect(self) -> None:
        email = self.entry.data[CONF_EMAIL]
        password = self.entry.data[CONF_PASSWORD]

        self.xsense = AsyncXSense()
        await self.xsense.init()

        try:
            await self.xsense.login(email, password)
        except AuthFailed as ex:
            raise ConfigEntryAuthFailed(f"Login failed: {str(ex)}") from ex
        LOGGER.debug("Logged in")

    async def _async_update_data(self) -> dict[str, Any]:
        if self.xsense is None:
            await self._connect()

        LOGGER.debug("_async_update_data")
        return await self.get_devices()

    async def get_all_devices(self, retry=False):
        """Retrieve all devices as a dict."""
        devices = {}
        try:
            await self.xsense.load_all()
            for _, h in self.xsense.houses.items():
                LOGGER.debug(f"house: {h}")
                for _, s in h.stations.items():
                    LOGGER.debug(f"station: {s}")
                    await self.xsense.get_state(s)
                    devices.update(s.devices.items())
            for k, v in devices.items():
                LOGGER.debug(f"{k}: {v}: {v.data}")
            return devices
        except (SessionExpired, AuthFailed) as ex:
            if not retry:
                await self._connect()
                return await self.get_all_devices(retry=True)
            raise ConfigEntryAuthFailed(
                "Could not update, session no longer valid"
            ) from ex
        except APIFailure as ex:
            raise UpdateFailed(f"XSense API Issue: {ex}") from ex

    async def get_stations(self, retry=False):
        """Retrieve all stations."""
        stations = []
        try:
            await self.xsense.load_all()
            for _, h in self.xsense.houses.items():
                LOGGER.info(f"house: {h}")
                for _, s in h.stations.items():
                    await self.xsense.get_station_state(s)
                    LOGGER.debug(f"station: {s}")
                    await self.xsense.get_state(s)
                    stations.append(s)
            return stations
        except (SessionExpired, AuthFailed) as ex:
            if not retry:
                await self._connect()
                return await self.get_stations(retry=True)
            raise ConfigEntryAuthFailed(
                "Could not update, session no longer valid"
            ) from ex
        except APIFailure as ex:
            raise UpdateFailed(f"XSense API Issue: {ex}") from ex

    async def get_devices(self, retry=False):
        """Retrieve all devices from the xsense account."""
        stations = {}
        devices = {}

        try:
            await self.xsense.load_all()

            for _, h in self.xsense.houses.items():
                stations.update(h.stations.items())
                with suppress(NotFoundError):
                    await self.xsense.get_house_state(h)
                for _, s in h.stations.items():
                    await self.xsense.get_station_state(s)
                    await self.xsense.get_state(s)
                    devices.update(s.devices.items())
            return {"stations": stations, "devices": devices}
        except (SessionExpired, AuthFailed) as ex:
            if not retry:
                await self._connect()
                return await self.get_devices(retry=True)
            raise ConfigEntryAuthFailed(
                "Could not update, session no longer valid"
            ) from ex
        except APIFailure as ex:
            raise UpdateFailed(f"XSense API Issue: {ex}") from ex
