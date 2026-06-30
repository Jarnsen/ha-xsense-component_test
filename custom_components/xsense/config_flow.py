"""Config flow for X-Sense Home Security integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import AsyncXSense
from .api.exceptions import APIFailure, AuthFailed
from .const import (
    CONF_RECORDING_MEDIA_CLIPS_ORDER,
    CONF_RECORDING_MEDIA_DAYS_ORDER,
    CONF_RECORDING_MEDIA_STORAGE_PATH,
    CONF_RECORDING_MEDIA_SYNC_ENABLED,
    CONF_RECORDING_MEDIA_SYNC_HOURS,
    DEFAULT_RECORDING_MEDIA_CLIPS_ORDER,
    DEFAULT_RECORDING_MEDIA_DAYS_ORDER,
    DEFAULT_RECORDING_MEDIA_STORAGE_PATH,
    DEFAULT_RECORDING_MEDIA_SYNC_ENABLED,
    DEFAULT_RECORDING_MEDIA_SYNC_HOURS,
    DOMAIN,
    RECORDING_MEDIA_ORDER_OPTIONS,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


def credentials_schema(default_email: str | None = None) -> vol.Schema:
    """Return the credentials schema, optionally prefilled with the current email."""
    return vol.Schema(
        {
            vol.Required(CONF_EMAIL, default=default_email): str,
            vol.Required(CONF_PASSWORD): str,
        }
    )


def options_schema(options: dict[str, Any] | None = None) -> vol.Schema:
    """Return the options schema."""
    options = _normalized_options(options or {})
    return vol.Schema(
        {
            vol.Optional(
                CONF_RECORDING_MEDIA_SYNC_ENABLED,
                default=options.get(
                    CONF_RECORDING_MEDIA_SYNC_ENABLED,
                    DEFAULT_RECORDING_MEDIA_SYNC_ENABLED,
                ),
            ): bool,
            vol.Optional(
                CONF_RECORDING_MEDIA_SYNC_HOURS,
                default=options.get(
                    CONF_RECORDING_MEDIA_SYNC_HOURS,
                    DEFAULT_RECORDING_MEDIA_SYNC_HOURS,
                ),
            ): vol.All(vol.Coerce(int), vol.Range(min=1, max=168)),
            vol.Optional(
                CONF_RECORDING_MEDIA_STORAGE_PATH,
                default=options.get(
                    CONF_RECORDING_MEDIA_STORAGE_PATH,
                    DEFAULT_RECORDING_MEDIA_STORAGE_PATH,
                ),
            ): vol.All(str, vol.Match(r"^/media(/.*)?$")),
            vol.Optional(
                CONF_RECORDING_MEDIA_DAYS_ORDER,
                default=options.get(
                    CONF_RECORDING_MEDIA_DAYS_ORDER,
                    DEFAULT_RECORDING_MEDIA_DAYS_ORDER,
                ),
            ): vol.In(RECORDING_MEDIA_ORDER_OPTIONS),
            vol.Optional(
                CONF_RECORDING_MEDIA_CLIPS_ORDER,
                default=options.get(
                    CONF_RECORDING_MEDIA_CLIPS_ORDER,
                    DEFAULT_RECORDING_MEDIA_CLIPS_ORDER,
                ),
            ): vol.In(RECORDING_MEDIA_ORDER_OPTIONS),
        }
    )


def recording_media_storage_path(options: dict[str, Any] | None = None) -> str:
    """Return the configured recording media storage path."""
    options = _normalized_options(options or {})
    return str(
        options.get(
            CONF_RECORDING_MEDIA_STORAGE_PATH,
            DEFAULT_RECORDING_MEDIA_STORAGE_PATH,
        )
    )


def recording_media_storage_path_changed(
    current_options: dict[str, Any] | None,
    new_options: dict[str, Any],
) -> bool:
    """Return whether the recording media storage path changed."""
    return recording_media_storage_path(current_options) != recording_media_storage_path(
        new_options
    )


def _normalized_options(options: dict[str, Any]) -> dict[str, Any]:
    """Return options with stale prerelease values made safe for the form."""
    normalized = dict(options)
    normalized[CONF_RECORDING_MEDIA_SYNC_ENABLED] = bool(
        normalized.get(
            CONF_RECORDING_MEDIA_SYNC_ENABLED,
            DEFAULT_RECORDING_MEDIA_SYNC_ENABLED,
        )
    )
    normalized[CONF_RECORDING_MEDIA_SYNC_HOURS] = _safe_sync_hours(
        normalized.get(CONF_RECORDING_MEDIA_SYNC_HOURS)
    )
    normalized[CONF_RECORDING_MEDIA_STORAGE_PATH] = _safe_media_path(
        normalized.get(CONF_RECORDING_MEDIA_STORAGE_PATH)
    )
    normalized[CONF_RECORDING_MEDIA_DAYS_ORDER] = _safe_order(
        normalized.get(CONF_RECORDING_MEDIA_DAYS_ORDER),
        DEFAULT_RECORDING_MEDIA_DAYS_ORDER,
    )
    normalized[CONF_RECORDING_MEDIA_CLIPS_ORDER] = _safe_order(
        normalized.get(CONF_RECORDING_MEDIA_CLIPS_ORDER),
        DEFAULT_RECORDING_MEDIA_CLIPS_ORDER,
    )
    return normalized


def _safe_sync_hours(value: Any) -> int:
    try:
        hours = int(value)
    except (TypeError, ValueError):
        return DEFAULT_RECORDING_MEDIA_SYNC_HOURS
    if 1 <= hours <= 168:
        return hours
    return DEFAULT_RECORDING_MEDIA_SYNC_HOURS


def _safe_media_path(value: Any) -> str:
    path = str(value or DEFAULT_RECORDING_MEDIA_STORAGE_PATH).strip()
    if path == "/media" or path.startswith("/media/"):
        return path
    return DEFAULT_RECORDING_MEDIA_STORAGE_PATH


def _safe_order(value: Any, default: str) -> str:
    text = str(value or "").strip()
    if text in RECORDING_MEDIA_ORDER_OPTIONS:
        return text
    lookup = text.lower().replace("_", " ").replace("-", " ")
    if lookup in {"ascending", "asc", "oldest", "oldest first"}:
        return "Ascending"
    if lookup in {"descending", "desc", "newest", "newest first"}:
        return "Descending"
    return default


async def _async_init_and_login(session: AsyncXSense, email, password) -> None:
    """Initialize the X-Sense client and log in."""
    await session.init()
    await session.login(email, password)


async def validate_input(hass: HomeAssistant, email, password) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """

    session = AsyncXSense(async_get_clientsession(hass))

    try:
        await _async_init_and_login(session, email, password)
    except AuthFailed as ex:
        raise InvalidAuth(f"Login failed: {str(ex)}") from ex
    except APIFailure as ex:
        raise CannotConnect from ex
    if not session.access_token:
        raise InvalidAuth

    # Return info that you want to store in the config entry.
    return {"title": f"XSense Account {session.username}"}


class XSenseConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for X-Sense Home Security."""

    VERSION = 1

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> XSenseOptionsFlow:
        """Return the options flow."""
        return XSenseOptionsFlow(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            email = user_input[CONF_EMAIL]
            password = user_input[CONF_PASSWORD]
            try:
                info = await validate_input(self.hass, email, password)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(email)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=info["title"],
                    data={CONF_EMAIL: email, CONF_PASSWORD: password},
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_reauth(self, user_input=None):
        """Perform reauth upon an API authentication error."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle re-authentication with XSense."""
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()

        if user_input is not None:
            email = user_input[CONF_EMAIL]
            password = user_input[CONF_PASSWORD]
            try:
                _ = await validate_input(self.hass, email, password)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(email)
                self._abort_if_unique_id_mismatch()
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates={CONF_EMAIL: email, CONF_PASSWORD: password},
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=credentials_schema(entry.data[CONF_EMAIL]),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle user-initiated credential updates."""
        errors: dict[str, str] = {}
        entry = self._get_reconfigure_entry()

        if user_input is not None:
            email = user_input[CONF_EMAIL]
            password = user_input[CONF_PASSWORD]
            try:
                _ = await validate_input(self.hass, email, password)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(email)
                self._abort_if_unique_id_mismatch()
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates={CONF_EMAIL: email, CONF_PASSWORD: password},
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=credentials_schema(entry.data[CONF_EMAIL]),
            errors=errors,
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""


class XSenseOptionsFlow(config_entries.OptionsFlow):
    """Handle X-Sense options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Set up the options flow."""
        self._options = dict(config_entry.options)
        self._pending_options: dict[str, Any] | None = None

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage X-Sense options."""
        if user_input is not None:
            if recording_media_storage_path_changed(self._options, user_input):
                self._pending_options = dict(user_input)
                return await self.async_step_confirm_recording_media_storage_path()
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=options_schema(self._options),
        )

    async def async_step_confirm_recording_media_storage_path(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirm recording media storage path changes."""
        if user_input is not None and self._pending_options is not None:
            return self.async_create_entry(title="", data=self._pending_options)

        pending_options = self._pending_options or self._options
        return self.async_show_form(
            step_id="confirm_recording_media_storage_path",
            data_schema=vol.Schema({}),
            description_placeholders={
                "old_path": recording_media_storage_path(self._options),
                "new_path": recording_media_storage_path(pending_options),
            },
        )
