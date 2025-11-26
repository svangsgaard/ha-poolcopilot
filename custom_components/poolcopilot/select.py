"""Select platform for Pool Copilot integration."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import PoolCopilotApiClient
from .const import DOMAIN
from .sensor import PoolCopilotDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Pool Copilot select entities from a config entry."""
    api_client: PoolCopilotApiClient = hass.data[DOMAIN][entry.entry_id]
    
    # Get the coordinator from sensor platform data
    coordinator_key = f"{entry.entry_id}_coordinator"
    if coordinator_key not in hass.data[DOMAIN]:
        coordinator = PoolCopilotDataUpdateCoordinator(hass, api_client)
        await coordinator.async_config_entry_first_refresh()
        hass.data[DOMAIN][coordinator_key] = coordinator
    else:
        coordinator = hass.data[DOMAIN][coordinator_key]

    # Check if pump has multiple speeds
    pump_data = coordinator.data.get("PoolCop", {}).get("settings", {}).get("pump", {})
    nb_speed = pump_data.get("nb_speed", 0)
    
    if nb_speed > 1:
        async_add_entities([PoolCopilotPumpSpeedSelect(coordinator, api_client, nb_speed)])


class PoolCopilotPumpSpeedSelect(CoordinatorEntity, SelectEntity):
    """Representation of a Pool Copilot pump speed select."""

    def __init__(
        self,
        coordinator: PoolCopilotDataUpdateCoordinator,
        api_client: PoolCopilotApiClient,
        nb_speed: int,
    ) -> None:
        """Initialize the select."""
        super().__init__(coordinator)
        self._api_client = api_client
        self._nb_speed = nb_speed
        self._attr_name = "Pump Speed"
        self._attr_unique_id = f"{DOMAIN}_pump_speed"
        self._attr_icon = "mdi:speedometer"
        
        # Create options based on number of speeds (0 = off, 1-3 = speed levels)
        self._attr_options = ["Off"] + [f"Speed {i}" for i in range(1, nb_speed + 1)]

    @property
    def current_option(self) -> str | None:
        """Return the current selected option."""
        if not self.coordinator.data:
            return None
        
        pump_status = self.coordinator.data.get("PoolCop", {}).get("status", {})
        pump_on = pump_status.get("pump")
        pump_speed = pump_status.get("pumpspeed", 0)
        
        if not pump_on:
            return "Off"
        
        # If pump is on but speed is 0, assume speed 1
        if pump_speed == 0:
            return "Speed 1"
        
        # Return the appropriate speed
        if 1 <= pump_speed <= self._nb_speed:
            return f"Speed {pump_speed}"
        
        return "Off"

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        try:
            if option == "Off":
                # Turn pump off
                await self._api_client.async_set_pump(turn_on=False)
            else:
                # Extract speed number from "Speed X"
                speed = int(option.split()[-1])
                await self._api_client.async_set_pump(turn_on=True, speed=speed)
            
            await asyncio.sleep(2)  # Wait for API to reflect changes
            await self.coordinator.async_request_refresh()
        except Exception as err:
            _LOGGER.error("Failed to set pump speed to %s: %s", option, err)
            raise

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        pump_data = self.coordinator.data.get("PoolCop", {}).get("settings", {}).get("pump", {})
        
        return {
            "number_of_speeds": self._nb_speed,
            "speed_cycle1": pump_data.get("speed_cycle1"),
            "speed_cycle2": pump_data.get("speed_cycle2"),
            "speed_backwash": pump_data.get("speed_backwash"),
            "speed_cover": pump_data.get("speed_cover"),
        }
