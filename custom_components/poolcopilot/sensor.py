"""Sensor platform for Pool Copilot integration."""
from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import PoolCopilotApiClient
from .const import CONF_SCAN_INTERVAL, DOMAIN, SCAN_INTERVAL_SECONDS, SENSOR_TYPES

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Pool Copilot sensors from a config entry."""
    api_client: PoolCopilotApiClient = hass.data[DOMAIN][entry.entry_id]

    scan_interval_seconds = entry.options.get(
        CONF_SCAN_INTERVAL,
        entry.data.get(
            CONF_SCAN_INTERVAL,
            hass.data[DOMAIN].get(CONF_SCAN_INTERVAL, SCAN_INTERVAL_SECONDS),
        ),
    )

    coordinator = PoolCopilotDataUpdateCoordinator(
        hass, api_client, scan_interval_seconds
    )
    await coordinator.async_config_entry_first_refresh()
    
    # Store coordinator for use by other platforms
    coordinator_key = f"{entry.entry_id}_coordinator"
    hass.data[DOMAIN][coordinator_key] = coordinator

    entities = []
    for sensor_type in SENSOR_TYPES:
        entities.append(PoolCopilotSensor(coordinator, sensor_type))

    async_add_entities(entities)


class PoolCopilotDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Pool Copilot data."""

    def __init__(
        self,
        hass: HomeAssistant,
        api_client: PoolCopilotApiClient,
        scan_interval_seconds: int,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval_seconds),
        )
        self.api_client = api_client

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from API."""
        try:
            data = await self.api_client.async_get_status()
            return data
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err


class PoolCopilotSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Pool Copilot sensor."""

    def __init__(
        self,
        coordinator: PoolCopilotDataUpdateCoordinator,
        sensor_type: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._sensor_type = sensor_type
        self._attr_name = SENSOR_TYPES[sensor_type]["name"]
        self._attr_unique_id = f"{DOMAIN}_{sensor_type}"
        self._attr_icon = SENSOR_TYPES[sensor_type]["icon"]
        self._attr_native_unit_of_measurement = SENSOR_TYPES[sensor_type]["unit"]
        
        device_class = SENSOR_TYPES[sensor_type].get("device_class")
        if device_class:
            self._attr_device_class = getattr(SensorDeviceClass, device_class.upper(), None)
        
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> float | int | bool | None:
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return None
        
        # Navigate through nested structure using path
        data = self.coordinator.data
        path = SENSOR_TYPES[self._sensor_type]["path"]
        
        for key in path:
            if isinstance(data, dict):
                data = data.get(key)
                if data is None:
                    return None
            else:
                return None
        
        return data

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success and self.native_value is not None
