"""Sensor platform for DE BLE Thermometer."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        TemperatureSensor(coordinator, entry),
        BatterySensor(coordinator, entry),
        ConnectionSensor(coordinator, entry),
    ])

class TemperatureSensor(SensorEntity, RestoreEntity):
    """Representation of temperature sensor."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_has_entity_name = True
    _attr_name = "Body Temperature"
    _attr_icon = "mdi:thermometer-probe"
    _attr_available = True
    _attr_should_poll = False

    def __init__(self, coordinator, entry):
        """Initialize the sensor."""
        self.coordinator = coordinator
        self._attr_unique_id = f"{entry.unique_id or entry.entry_id}_temperature"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.address)},
        )
        self._async_unsub_dispatcher = None
        self._attr_native_value = 0.0
        self._received_first_update = False

    async def async_added_to_hass(self) -> None:
        """Restore last state."""
        await super().async_added_to_hass()
        
        if (last_state := await self.async_get_last_state()) is not None:
            try:
                restored_value = float(last_state.state)
                # Проверяем, что восстановленное значение в разумных пределах
                if 25.0 <= restored_value <= 45.0:
                    self._attr_native_value = restored_value
                    _LOGGER.debug(f"Restored {self.entity_id} = {self._attr_native_value}")
            except (ValueError, TypeError):
                _LOGGER.debug("Could not restore state for %s", self.entity_id)
        
        @callback
        def update(source: str, data: Any) -> None:
            """Update state."""
            if source == "temperature":
                # Если это первое обновление, обновляем всегда (даже если 0)
                if not self._received_first_update:
                    self._attr_native_value = data
                    self._received_first_update = True
                    self.async_write_ha_state()
                # Если не первое обновление, обновляем только если значение изменилось
                elif self._attr_native_value != data:
                    self._attr_native_value = data
                    self.async_write_ha_state()
        
        self._async_unsub_dispatcher = async_dispatcher_connect(
            self.hass, f"{DOMAIN}_{self.coordinator.entry_id}_update", update
        )
    
    async def async_will_remove_from_hass(self) -> None:
        """Run when entity will be removed."""
        if self._async_unsub_dispatcher:
            self._async_unsub_dispatcher()
        await super().async_will_remove_from_hass()
    
    @property
    def native_value(self) -> float:
        """Return the state."""
        return self._attr_native_value

class BatterySensor(SensorEntity, RestoreEntity):
    """Representation of battery sensor."""

    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_has_entity_name = True
    _attr_name = "Battery"
    _attr_icon = "mdi:battery"
    _attr_available = True
    _attr_should_poll = False

    def __init__(self, coordinator, entry):
        """Initialize the sensor."""
        self.coordinator = coordinator
        self._attr_unique_id = f"{entry.unique_id or entry.entry_id}_battery"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.address)},
        )
        self._async_unsub_dispatcher = None
        self._attr_native_value = 0
        self._received_first_update = False

    async def async_added_to_hass(self) -> None:
        """Restore last state."""
        await super().async_added_to_hass()
        
        if (last_state := await self.async_get_last_state()) is not None:
            try:
                restored_value = int(float(last_state.state))
                # Проверяем, что восстановленное значение в разумных пределах
                if 0 <= restored_value <= 100:
                    self._attr_native_value = restored_value
                    _LOGGER.debug(f"Restored {self.entity_id} = {self._attr_native_value}")
            except (ValueError, TypeError):
                _LOGGER.debug("Could not restore state for %s", self.entity_id)
        
        @callback
        def update(source: str, data: Any) -> None:
            """Update state."""
            if source == "battery":
                # Если это первое обновление, обновляем всегда
                if not self._received_first_update:
                    if 0 <= data <= 100:  # Проверяем, что данные валидны
                        self._attr_native_value = data
                        self._received_first_update = True
                        self.async_write_ha_state()
                # Если не первое обновление, обновляем только если значение изменилось
                elif self._attr_native_value != data and 0 <= data <= 100:
                    self._attr_native_value = data
                    self.async_write_ha_state()
        
        self._async_unsub_dispatcher = async_dispatcher_connect(
            self.hass, f"{DOMAIN}_{self.coordinator.entry_id}_update", update
        )
    
    async def async_will_remove_from_hass(self) -> None:
        """Run when entity will be removed."""
        if self._async_unsub_dispatcher:
            self._async_unsub_dispatcher()
        await super().async_will_remove_from_hass()
    
    @property
    def native_value(self) -> int:
        """Return the state."""
        return self._attr_native_value

class ConnectionSensor(SensorEntity):
    """Representation of connection status."""

    _attr_has_entity_name = True
    _attr_name = "Connection Status"
    _attr_icon = "mdi:bluetooth-connect"
    _attr_should_poll = False

    def __init__(self, coordinator, entry):
        """Initialize the sensor."""
        self.coordinator = coordinator
        self._attr_unique_id = f"{entry.unique_id or entry.entry_id}_connection"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.address)},
        )
        self._async_unsub_dispatcher = None

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added."""
        await super().async_added_to_hass()
        
        @callback
        def update(source: str, data: Any) -> None:
            """Update state."""
            if source in ["connected", "disconnected", "blocked"]:
                self.async_write_ha_state()
        
        self._async_unsub_dispatcher = async_dispatcher_connect(
            self.hass, f"{DOMAIN}_{self.coordinator.entry_id}_update", update
        )
    
    async def async_will_remove_from_hass(self) -> None:
        """Run when entity will be removed."""
        if self._async_unsub_dispatcher:
            self._async_unsub_dispatcher()
        await super().async_will_remove_from_hass()
    
    @property
    def native_value(self) -> str:
        """Return the state."""
        if self.coordinator.blocked:
            return "Blocked"
        elif self.coordinator.connected:
            return "Connected"
        return "Disconnected"
    
    @property
    def icon(self) -> str:
        """Return icon based on connection state."""
        if self.coordinator.blocked:
            return "mdi:clock-outline"
        elif self.coordinator.connected:
            return "mdi:bluetooth-connect"
        return "mdi:bluetooth-off"
