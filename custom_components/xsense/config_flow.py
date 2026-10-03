"""Config flow for X-Sense Home Security integration."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path, PurePosixPath
from stat import S_ISDIR
from typing import Any

from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import AbortFlow, FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import selector
from homeassistant.helpers import entity_registry as er

import voluptuous as vol

from .python_xsense import AsyncXSense
from .python_xsense.async_xsense import is_camera_entity
from .python_xsense.exceptions import APIFailure, AuthFailed
from .const import (
    CONF_RECORDING_CACHE_MAX_SIZE_MB,
    CONF_RECORDING_CACHE_MODE,
    CONF_RECORDING_CACHE_RETENTION_DAYS,
    CONF_RECORDING_MEDIA_CLIPS_ORDER,
    CONF_RECORDING_MEDIA_DAYS_ORDER,
    CONF_RECORDING_MEDIA_STORAGE_PATH,
    CONF_RECORDING_MEDIA_SYNC_ENABLED,
    CONF_RECORDING_MEDIA_SYNC_HOURS,
    CONF_RECORDING_NOTIFICATION_QUALITY,
    DEFAULT_RECORDING_CACHE_MAX_SIZE_MB,
    DEFAULT_RECORDING_CACHE_MODE,
    DEFAULT_RECORDING_CACHE_RETENTION_DAYS,
    DEFAULT_RECORDING_MEDIA_CLIPS_ORDER,
    DEFAULT_RECORDING_MEDIA_DAYS_ORDER,
    DEFAULT_RECORDING_MEDIA_STORAGE_PATH,
    DEFAULT_RECORDING_MEDIA_SYNC_ENABLED,
    DEFAULT_RECORDING_MEDIA_SYNC_HOURS,
    DEFAULT_RECORDING_NOTIFICATION_QUALITY,
    DOMAIN,
    RECORDING_CACHE_MODE_OPTIONS,
    RECORDING_MEDIA_ORDER_OPTIONS,
    RECORDING_NOTIFICATION_QUALITY_OPTIONS,
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


def options_schema(
    options: dict[str, Any] | None = None, *, include_recording_options: bool = True
) -> vol.Schema:
    """Return the options schema."""
    options = _normalized_options(options or {})
    if not include_recording_options:
        return vol.Schema({})

    return vol.Schema(
        {
            vol.Optional(
                CONF_RECORDING_CACHE_MODE,
                default=options.get(
                    CONF_RECORDING_CACHE_MODE,
                    DEFAULT_RECORDING_CACHE_MODE,
                ),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=RECORDING_CACHE_MODE_OPTIONS,
                    translation_key=CONF_RECORDING_CACHE_MODE,
                )
            ),
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
            ): str,
            vol.Optional(
                CONF_RECORDING_CACHE_RETENTION_DAYS,
                default=options.get(
                    CONF_RECORDING_CACHE_RETENTION_DAYS,
                    DEFAULT_RECORDING_CACHE_RETENTION_DAYS,
                ),
            ): vol.All(vol.Coerce(int), vol.Range(min=1, max=365)),
            vol.Optional(
                CONF_RECORDING_CACHE_MAX_SIZE_MB,
                default=options.get(
                    CONF_RECORDING_CACHE_MAX_SIZE_MB,
                    DEFAULT_RECORDING_CACHE_MAX_SIZE_MB,
                ),
            ): vol.All(vol.Coerce(int), vol.Range(min=128, max=102400)),
            vol.Optional(
                CONF_RECORDING_NOTIFICATION_QUALITY,
                default=options.get(
                    CONF_RECORDING_NOTIFICATION_QUALITY,
                    DEFAULT_RECORDING_NOTIFICATION_QUALITY,
                ),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=RECORDING_NOTIFICATION_QUALITY_OPTIONS,
                    translation_key=CONF_RECORDING_NOTIFICATION_QUALITY,
                )
            ),
            vol.Optional(
                CONF_RECORDING_MEDIA_DAYS_ORDER,
                default=options.get(
                    CONF_RECORDING_MEDIA_DAYS_ORDER,
                    DEFAULT_RECORDING_MEDIA_DAYS_ORDER,
                ),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=RECORDING_MEDIA_ORDER_OPTIONS,
                    translation_key=CONF_RECORDING_MEDIA_DAYS_ORDER,
                )
            ),
            vol.Optional(
                CONF_RECORDING_MEDIA_CLIPS_ORDER,
                default=options.get(
                    CONF_RECORDING_MEDIA_CLIPS_ORDER,
                    DEFAULT_RECORDING_MEDIA_CLIPS_ORDER,
                ),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=RECORDING_MEDIA_ORDER_OPTIONS,
                    translation_key=CONF_RECORDING_MEDIA_CLIPS_ORDER,
                )
            ),
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
    normalized[CONF_RECORDING_CACHE_MODE] = _safe_cache_mode(
        normalized.get(CONF_RECORDING_CACHE_MODE)
    )
    normalized[CONF_RECORDING_MEDIA_SYNC_ENABLED] = bool(
        normalized.get(
            CONF_RECORDING_MEDIA_SYNC_ENABLED,
            DEFAULT_RECORDING_MEDIA_SYNC_ENABLED,
        )
    ) and normalized[CONF_RECORDING_CACHE_MODE] == "retained"
    normalized[CONF_RECORDING_MEDIA_SYNC_HOURS] = _safe_sync_hours(
        normalized.get(CONF_RECORDING_MEDIA_SYNC_HOURS)
    )
    normalized[CONF_RECORDING_MEDIA_STORAGE_PATH] = _safe_media_path(
        normalized.get(CONF_RECORDING_MEDIA_STORAGE_PATH)
    )
    normalized[CONF_RECORDING_CACHE_RETENTION_DAYS] = _safe_int_option(
        normalized.get(CONF_RECORDING_CACHE_RETENTION_DAYS),
        DEFAULT_RECORDING_CACHE_RETENTION_DAYS,
        minimum=1,
        maximum=365,
    )
    normalized[CONF_RECORDING_CACHE_MAX_SIZE_MB] = _safe_int_option(
        normalized.get(CONF_RECORDING_CACHE_MAX_SIZE_MB),
        DEFAULT_RECORDING_CACHE_MAX_SIZE_MB,
        minimum=128,
        maximum=102400,
    )
    normalized[CONF_RECORDING_NOTIFICATION_QUALITY] = _safe_recording_quality(
        normalized.get(CONF_RECORDING_NOTIFICATION_QUALITY)
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


def _safe_cache_mode(value: Any) -> str:
    mode = str(value or DEFAULT_RECORDING_CACHE_MODE).strip().lower()
    if mode in RECORDING_CACHE_MODE_OPTIONS:
        return mode
    return DEFAULT_RECORDING_CACHE_MODE


def _safe_sync_hours(value: Any) -> int:
    try:
        hours = int(value)
    except (TypeError, ValueError, OverflowError):
        return DEFAULT_RECORDING_MEDIA_SYNC_HOURS
    if 1 <= hours <= 168:
        return hours
    return DEFAULT_RECORDING_MEDIA_SYNC_HOURS


def _safe_int_option(
    value: Any, default: int, *, minimum: int, maximum: int
) -> int:
    """Return one bounded integer option without leaking stale values."""
    try:
        result = int(value)
    except (TypeError, ValueError, OverflowError):
        return default
    return result if minimum <= result <= maximum else default


def _safe_media_path(value: Any) -> str:
    path = str(value or DEFAULT_RECORDING_MEDIA_STORAGE_PATH).strip()
    if _recording_media_path_allowed(path):
        return path
    return DEFAULT_RECORDING_MEDIA_STORAGE_PATH


def _recording_media_path_allowed(value: Any) -> bool:
    """Return whether a recording media path stays under Home Assistant media."""
    path = str(value or "").strip()
    lexical = PurePosixPath(path)
    if not lexical.is_absolute() or ".." in lexical.parts or "\x00" in path:
        return False
    if lexical != PurePosixPath("/media") and PurePosixPath("/media") not in lexical.parents:
        return False
    try:
        return Path(path).resolve().is_relative_to(Path("/media").resolve())
    except (OSError, RuntimeError, ValueError):
        return False


def _validated_options(options: dict[str, Any]) -> dict[str, Any] | None:
    """Validate filesystem destinations in an executor, without creating anything."""
    path = str(options.get(CONF_RECORDING_MEDIA_STORAGE_PATH) or "").strip()
    if not _recording_media_path_allowed(path):
        return None
    candidate = Path(path)
    try:
        # A missing directory is allowed, but every existing ancestor must be a directory.
        while True:
            try:
                if not S_ISDIR(candidate.stat().st_mode):
                    return None
                break
            except FileNotFoundError:
                if candidate == candidate.parent:
                    return None
                candidate = candidate.parent
    except (OSError, RuntimeError, ValueError):
        return None
    normalized = _normalized_options(options)
    normalized[CONF_RECORDING_MEDIA_STORAGE_PATH] = path
    return normalized


def _safe_order(value: Any, default: str) -> str:
    text = str(value or "").strip()
    if text in RECORDING_MEDIA_ORDER_OPTIONS:
        return text
    lookup = text.lower().replace("_", " ").replace("-", " ")
    if lookup in {"ascending", "asc", "oldest", "oldest first"}:
        return "ascending"
    if lookup in {"descending", "desc", "newest", "newest first"}:
        return "descending"
    return default


def _safe_recording_quality(value: Any) -> str:
    text = str(value or "").strip().lower()
    if text in RECORDING_NOTIFICATION_QUALITY_OPTIONS:
        return text
    return DEFAULT_RECORDING_NOTIFICATION_QUALITY


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
                return self.async_update_and_abort(
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
                return self.async_update_and_abort(
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


def _effective_options(entry: config_entries.ConfigEntry) -> dict[str, Any]:
    """Read only legacy data keys still consumed by recording runtime."""
    legacy_data = getattr(entry, "data", {})
    options = {
        key: legacy_data[key]
        for key in (
            CONF_RECORDING_MEDIA_STORAGE_PATH,
            CONF_RECORDING_MEDIA_DAYS_ORDER,
            CONF_RECORDING_MEDIA_CLIPS_ORDER,
        )
        if key in legacy_data
    }
    options.update(entry.options)
    return options


class XSenseOptionsFlow(config_entries.OptionsFlow):
    """Handle X-Sense options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Set up the options flow."""
        self._entry = config_entry
        self._entry_id = getattr(config_entry, "entry_id", "")
        self._pending_options: dict[str, Any] | None = None
        self._confirmation_old_path: str | None = None

    def _current_options(self) -> dict[str, Any]:
        entries = getattr(getattr(self, "hass", None), "config_entries", None)
        getter = getattr(entries, "async_get_entry", None)
        entry = getter(self._entry_id) if callable(getter) else self._entry
        if entry is None:
            raise AbortFlow("no_options")
        return _effective_options(entry)

    async def _async_in_executor(self, func, *args):
        executor = getattr(getattr(self, "hass", None), "async_add_executor_job", None)
        if executor is not None:
            return await executor(func, *args)
        return await asyncio.to_thread(func, *args)

    async def _async_current_options(self) -> dict[str, Any]:
        while True:
            options = self._current_options()
            normalized = await self._async_in_executor(_normalized_options, options)
            # Another flow may save while filesystem normalization is running.
            if options == self._current_options():
                return normalized

    async def _async_options_form(self, values, errors=None) -> FlowResult:
        schema = await self._async_in_executor(options_schema, values)
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(schema, values),
            errors=errors or {},
        )

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage X-Sense options."""
        include_recording_options = _entry_has_cameras(
            getattr(self, "hass", None), self._entry_id
        )
        if not include_recording_options:
            return self.async_abort(reason="no_options")

        if user_input is not None:
            validated = await self._async_in_executor(_validated_options, user_input)
            if validated is None:
                return await self._async_options_form(user_input, {
                    CONF_RECORDING_MEDIA_STORAGE_PATH: "invalid_recording_media_path",
                })
            current = await self._async_current_options()
            if current[CONF_RECORDING_MEDIA_STORAGE_PATH] == validated[CONF_RECORDING_MEDIA_STORAGE_PATH]:
                return self.async_create_entry(title="", data=validated)
            self._pending_options = validated
            return await self.async_step_confirm_recording_media_storage_path()

        return await self._async_options_form(await self._async_current_options())

    async def async_step_confirm_recording_media_storage_path(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirm recording media storage path changes."""
        if self._pending_options is None:
            return await self.async_step_init()
        if not _entry_has_cameras(getattr(self, "hass", None), self._entry_id):
            return self.async_abort(reason="no_options")
        pending_options = await self._async_in_executor(_validated_options, self._pending_options)
        if pending_options is None:
            values, self._pending_options = self._pending_options, None
            return await self._async_options_form(values, {
                CONF_RECORDING_MEDIA_STORAGE_PATH: "invalid_recording_media_path",
            })
        current = await self._async_current_options()
        old_path = current[CONF_RECORDING_MEDIA_STORAGE_PATH]
        new_path = pending_options[CONF_RECORDING_MEDIA_STORAGE_PATH]
        if user_input is not None and old_path in (new_path, self._confirmation_old_path):
            return self.async_create_entry(title="", data=pending_options)
        self._confirmation_old_path = old_path
        return self.async_show_form(
            step_id="confirm_recording_media_storage_path",
            data_schema=vol.Schema({}),
            description_placeholders={
                "old_path": old_path,
                "new_path": new_path,
            },
        )


def _entry_has_cameras(hass: HomeAssistant | None, entry_id: str) -> bool:
    """Use loaded inventory, or entry-owned camera records when unavailable."""
    if hass is None:
        return True

    coordinator = hass.data.get(DOMAIN, {}).get(entry_id)
    data = getattr(coordinator, "data", None)
    if not isinstance(data, dict):
        registry = er.async_get(hass)
        return any(
            entity.domain == "camera" and entity.platform == DOMAIN
            for entity in er.async_entries_for_config_entry(registry, entry_id)
        )

    for entity in (
        *data.get("stations", {}).values(),
        *data.get("devices", {}).values(),
    ):
        try:
            if is_camera_entity(entity):
                return True
        except AttributeError:
            continue
    return False
