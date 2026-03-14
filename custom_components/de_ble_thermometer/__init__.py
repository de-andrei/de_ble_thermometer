"""DE BLE Thermometer integration."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS, EVENT_HOMEASSISTANT_STOP
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_time_interval

from .const import (
    DOMAIN,
    DEVICE_MANUFACTURER,
    DEVICE_MODEL,
    SCAN_INTERVAL,
    BLOCK_DURATION,
)
from .ble_device import RelsibWT50

_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(logging.WARNING)

PLATFORMS = ["sensor", "button"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up DE BLE Thermometer from a config entry."""
    address = entry.data[CONF_ADDRESS]
    
    coordinator = ThermometerCoordinator(hass, address, entry.entry_id)
    await coordinator.async_setup()
    
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    
    async def _async_shutdown(event):
        await coordinator.async_shutdown()
    
    entry.async_on_unload(
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, _async_shutdown)
    )
    
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        coordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.async_shutdown()
    
    return unload_ok

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the DE BLE Thermometer integration."""
    hass.data.setdefault(DOMAIN, {})
    return True

class ThermometerCoordinator:
    """Coordinator for Thermometer BLE."""
    
    def __init__(self, hass: HomeAssistant, address: str, entry_id: str) -> None:
        """Initialize coordinator."""
        self.hass = hass
        self.address = address
        self.entry_id = entry_id
        self.device: RelsibWT50 | None = None
        self._connected = False
        self._temperature = 0.0
        self._battery = 0
        self._block_until = 0
        self._cancel_scan: callable | None = None
        self._connecting = False
        self._shutdown = False
        
    async def async_setup(self) -> None:
        """Set up coordinator."""
        self.device = RelsibWT50(self.address)
        self.device.set_callback(self._handle_update)
        
        await self._register_device()
        
        self._cancel_scan = async_track_time_interval(
            self.hass, self._try_connect, SCAN_INTERVAL
        )
        
        for _ in range(3):
            await self._try_connect()
            if self._connected:
                break
            await asyncio.sleep(1)
        
    async def _register_device(self) -> None:
        """Register device in device registry."""
        device_registry = dr.async_get(self.hass)
        device_registry.async_get_or_create(
            config_entry_id=self.entry_id,
            identifiers={(DOMAIN, self.address)},
            name="Thermometer",
            manufacturer=DEVICE_MANUFACTURER,
            model=DEVICE_MODEL,
            connections={(dr.CONNECTION_BLUETOOTH, self.address)},
        )
    
    @callback
    def _handle_update(self, source: str, data: Any) -> None:
        """Handle updates from device."""
        if source == "temperature":
            self._temperature = data
            async_dispatcher_send(
                self.hass, f"{DOMAIN}_{self.entry_id}_update", "temperature", data
            )
        elif source == "battery":
            self._battery = data
            async_dispatcher_send(
                self.hass, f"{DOMAIN}_{self.entry_id}_update", "battery", data
            )
        elif source == "connected":
            self._connected = True
            self._connecting = False
            async_dispatcher_send(
                self.hass, f"{DOMAIN}_{self.entry_id}_update", "connected", None
            )
        elif source == "disconnected":
            self._connected = False
            self._connecting = False
            async_dispatcher_send(
                self.hass, f"{DOMAIN}_{self.entry_id}_update", "disconnected", None
            )
    
    async def _try_connect(self, now=None) -> None:
        """Try to connect to device."""
        if self._shutdown:
            return
        
        # Проверяем блокировку
        now_ms = int(asyncio.get_event_loop().time() * 1000)
        if now_ms < self._block_until:
            if self._connected:
                await self.async_disconnect()
            return
            
        if self._connected or self._connecting:
            return
            
        self._connecting = True
        
        try:
            if self.device:
                self.device.set_block_until(self._block_until)
                success = await self.device.async_connect()
                if not success:
                    self._connecting = False
        except Exception:
            self._connecting = False
    
    async def async_stop_thermometer(self) -> None:
        """Stop thermometer for 3.5 minutes."""
        now_ms = int(asyncio.get_event_loop().time() * 1000)
        self._block_until = now_ms + BLOCK_DURATION
        
        if self.device:
            self.device.set_block_until(self._block_until)
            if self.device.connected:
                await self.device.async_disconnect()
        
        async_dispatcher_send(
            self.hass, f"{DOMAIN}_{self.entry_id}_update", "blocked", None
        )
    
    async def async_disconnect(self) -> None:
        """Disconnect from device."""
        if self.device and self.device.connected:
            await self.device.async_disconnect()
    
    async def async_shutdown(self) -> None:
        """Shutdown coordinator."""
        self._shutdown = True
        
        if self._cancel_scan:
            self._cancel_scan()
            self._cancel_scan = None
        
        if self.device:
            if self.device.connected:
                await self.device.async_disconnect()
            self.device = None
    
    @property
    def temperature(self) -> float:
        """Current temperature."""
        return self._temperature
    
    @property
    def battery(self) -> int:
        """Current battery level."""
        return self._battery
    
    @property
    def connected(self) -> bool:
        """Connection status (respects blocking)."""
        now_ms = int(asyncio.get_event_loop().time() * 1000)
        if now_ms < self._block_until:
            return False
        return self._connected
    
    @property
    def blocked(self) -> bool:
        """Blocked status."""
        now_ms = int(asyncio.get_event_loop().time() * 1000)
        return now_ms < self._block_until
