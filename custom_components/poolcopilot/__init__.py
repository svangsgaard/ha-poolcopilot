"""The Pool Copilot integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .api import PoolCopilotApiClient
from .const import CONF_API_KEY, CONF_SCAN_INTERVAL, DOMAIN, SCAN_INTERVAL_SECONDS

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.SWITCH, Platform.SELECT]

CONFIG_SCHEMA = vol.Schema(
    {
        vol.Optional(DOMAIN, default={}): vol.Schema(
            {
                vol.Optional(CONF_SCAN_INTERVAL, default=SCAN_INTERVAL_SECONDS): vol.All(
                    cv.positive_int, vol.Range(min=10)
                )
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up Pool Copilot from YAML configuration."""
    domain_config: dict[str, Any] = config.get(DOMAIN, {})

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][CONF_SCAN_INTERVAL] = domain_config.get(
        CONF_SCAN_INTERVAL, SCAN_INTERVAL_SECONDS
    )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Pool Copilot from a config entry."""
    api_key = entry.data[CONF_API_KEY]

    api_client = PoolCopilotApiClient(api_key)

    # Verify API connection
    try:
        await api_client.async_get_status()
    except Exception as err:
        _LOGGER.error("Failed to connect to Pool Copilot API: %s", err)
        raise ConfigEntryNotReady from err
    
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = api_client

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    
    return unload_ok
