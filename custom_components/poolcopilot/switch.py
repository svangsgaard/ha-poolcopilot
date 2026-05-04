"""Switch platform for Pool Copilot integration."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import PoolCopilotApiClient
from .const import CONF_SCAN_INTERVAL, DOMAIN, SCAN_INTERVAL_SECONDS
from .sensor import PoolCopilotDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Pool Copilot switches from a config entry."""
    api_client: PoolCopilotApiClient = hass.data[DOMAIN][entry.entry_id]
    
    # Get the coordinator from sensor platform data
    coordinator_key = f"{entry.entry_id}_coordinator"
    if coordinator_key not in hass.data[DOMAIN]:
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
        hass.data[DOMAIN][coordinator_key] = coordinator
    else:
        coordinator = hass.data[DOMAIN][coordinator_key]

    switches = [
        PoolCopilotPumpSwitch(coordinator, api_client),
    ]
    
    # Add auxiliary switches
    aux_data = coordinator.data.get("PoolCop", {}).get("aux", [])
    for aux in aux_data:
        aux_id = aux.get("id")
        switchable = aux.get("switchable", True)
        if aux_id and switchable:
            switches.append(PoolCopilotAuxSwitch(coordinator, api_client, aux))
    
    async_add_entities(switches)


class PoolCopilotPumpSwitch(CoordinatorEntity, SwitchEntity):
    """Representation of a Pool Copilot pump switch."""

    def __init__(
        self,
        coordinator: PoolCopilotDataUpdateCoordinator,
        api_client: PoolCopilotApiClient,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._api_client = api_client
        self._optimistic_is_on: bool | None = None
        self._attr_name = "Pump"
        self._attr_unique_id = f"{DOMAIN}_pump"
        self._attr_icon = "mdi:pump"

    def _coordinator_is_on(self) -> bool | None:
        """Return the current coordinator state."""
        if not self.coordinator.data:
            return None

        status = self.coordinator.data.get("PoolCop", {}).get("status", {}).get("pump")
        return bool(status) if status is not None else None

    @property
    def is_on(self) -> bool | None:
        """Return true if the pump is on."""
        if self._optimistic_is_on is not None:
            return self._optimistic_is_on

        return self._coordinator_is_on()

    @property
    def assumed_state(self) -> bool:
        """Return whether the displayed state is optimistic."""
        return self._optimistic_is_on is not None

    async def _async_apply_state(self, turn_on: bool) -> None:
        """Apply the requested state and wait briefly for backend confirmation."""
        self._optimistic_is_on = turn_on
        self.async_write_ha_state()

        try:
            await self._api_client.async_set_pump(turn_on=turn_on)

            for _ in range(5):
                await asyncio.sleep(1)
                await self.coordinator.async_request_refresh()
                if self._coordinator_is_on() == turn_on:
                    break
        except Exception:
            self._optimistic_is_on = None
            self.async_write_ha_state()
            raise

        self._optimistic_is_on = None
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the pump on."""
        try:
            await self._async_apply_state(True)
        except Exception as err:
            _LOGGER.error("Failed to turn on pump: %s", err)
            raise

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the pump off."""
        try:
            await self._async_apply_state(False)
        except Exception as err:
            _LOGGER.error("Failed to turn off pump: %s", err)
            raise

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success and self.is_on is not None

    @callback
    def _handle_coordinator_update(self) -> None:
        """Clear optimistic state once the coordinator confirms it."""
        if self._optimistic_is_on is not None and self._coordinator_is_on() == self._optimistic_is_on:
            self._optimistic_is_on = None

        super()._handle_coordinator_update()


class PoolCopilotAuxSwitch(CoordinatorEntity, SwitchEntity):
    """Representation of a Pool Copilot auxiliary switch."""

    def __init__(
        self,
        coordinator: PoolCopilotDataUpdateCoordinator,
        api_client: PoolCopilotApiClient,
        aux_data: dict[str, Any],
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._api_client = api_client
        self._optimistic_is_on: bool | None = None
        self._aux_id = aux_data["id"]
        self._aux_label = aux_data.get("label", f"Aux {self._aux_id}")
        self._attr_name = self._aux_label
        self._attr_unique_id = f"{DOMAIN}_aux_{self._aux_id}"
        self._attr_icon = "mdi:electric-switch"

    def _coordinator_is_on(self) -> bool | None:
        """Return the current coordinator state."""
        if not self.coordinator.data:
            return None

        aux_list = self.coordinator.data.get("PoolCop", {}).get("aux", [])
        for aux in aux_list:
            if aux.get("id") == self._aux_id:
                status = aux.get("status")
                return bool(status) if status is not None else None

        return None

    @property
    def is_on(self) -> bool | None:
        """Return true if the auxiliary is on."""
        if self._optimistic_is_on is not None:
            return self._optimistic_is_on

        return self._coordinator_is_on()

    @property
    def assumed_state(self) -> bool:
        """Return whether the displayed state is optimistic."""
        return self._optimistic_is_on is not None

    async def _async_apply_state(self, turn_on: bool) -> None:
        """Apply the requested state and wait briefly for backend confirmation."""
        self._optimistic_is_on = turn_on
        self.async_write_ha_state()

        try:
            await self._api_client.async_set_aux(self._aux_id)

            for _ in range(5):
                await asyncio.sleep(1)
                await self.coordinator.async_request_refresh()
                if self._coordinator_is_on() == turn_on:
                    break
        except Exception:
            self._optimistic_is_on = None
            self.async_write_ha_state()
            raise

        self._optimistic_is_on = None
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the auxiliary on."""
        try:
            await self._async_apply_state(True)
        except Exception as err:
            _LOGGER.error("Failed to toggle aux %s: %s", self._aux_id, err)
            raise

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the auxiliary off."""
        try:
            await self._async_apply_state(False)
        except Exception as err:
            _LOGGER.error("Failed to toggle aux %s: %s", self._aux_id, err)
            raise

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success and self.is_on is not None

    @callback
    def _handle_coordinator_update(self) -> None:
        """Clear optimistic state once the coordinator confirms it."""
        if self._optimistic_is_on is not None and self._coordinator_is_on() == self._optimistic_is_on:
            self._optimistic_is_on = None

        super()._handle_coordinator_update()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        if not self.coordinator.data:
            return {}
        
        aux_list = self.coordinator.data.get("PoolCop", {}).get("aux", [])
        for aux in aux_list:
            if aux.get("id") == self._aux_id:
                attributes = {
                    "aux_id": self._aux_id,
                    "slave": aux.get("slave", False),
                    "days": aux.get("days", []),
                }
                
                # Add heating setpoint if available
                if "heating_setpoint" in aux:
                    attributes["heating_setpoint"] = aux["heating_setpoint"]
                
                return attributes
        
        return {}
