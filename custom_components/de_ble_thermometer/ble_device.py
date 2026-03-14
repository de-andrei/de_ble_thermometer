"""Async Python library for Relsib WT50 Thermometer."""

import asyncio
import logging
import math
from typing import Optional, Callable, Any, Union

from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice

_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(logging.WARNING)

# UUIDs
TEMP_SERVICE_UUID = "00001809-0000-1000-8000-00805f9b34fb"
TEMP_CHAR_UUID = "00002a1e-0000-1000-8000-00805f9b34fb"
BATTERY_SERVICE_UUID = "0000180f-0000-1000-8000-00805f9b34fb"
BATTERY_CHAR_UUID = "00002a19-0000-1000-8000-00805f9b34fb"

class RelsibWT50:
    """Relsib WT50 Thermometer interface."""
    
    def __init__(self, address_or_ble_device: Union[str, BLEDevice]):
        """Initialize thermometer with address or BLEDevice."""
        if isinstance(address_or_ble_device, BLEDevice):
            self.address = address_or_ble_device.address
            self.ble_device = address_or_ble_device
        else:
            self.address = address_or_ble_device
            self.ble_device = None
            
        self.client: Optional[BleakClient] = None
        self._temperature: float = 0.0
        self._battery: int = 0
        self._block_until: int = 0
        self._callback: Optional[Callable[[str, Any], None]] = None
        
    def set_callback(self, callback: Callable[[str, Any], None]) -> None:
        """Set callback for data updates."""
        self._callback = callback
        
    def set_block_until(self, block_until: int) -> None:
        """Set block timestamp."""
        self._block_until = block_until
        
    def _temp_notification_handler(self, sender: int, data: bytearray) -> None:
        """Handle temperature notifications."""
        try:
            # Проверяем размер данных
            if len(data) != 5:
                return
            
            flags = data[0]
            fahrenheit = (flags & 0x01) == 0x01
            
            # Извлекаем мантиссу (24 бита) - просто как в ESPHome
            mantissa = (data[1] | (data[2] << 8) | (data[3] << 16))
            exponent = data[4]
            
            # Преобразуем exponent из signed byte
            if exponent > 127:
                exponent = exponent - 256
            
            # Вычисляем температуру
            temperature = mantissa * (10 ** exponent)
            
            if fahrenheit:
                temperature = (temperature - 32) * 5.0 / 9.0
            
            # Округляем до 1 знака
            temperature = round(temperature, 1)
            
            # Жесткая проверка: только температуры от 25 до 45 градусов
            if 25.0 <= temperature <= 45.0:
                self._temperature = temperature
                if self._callback:
                    self._callback("temperature", temperature)
            
        except Exception:
            pass
    
    def _battery_notification_handler(self, sender: int, data: bytearray) -> None:
        """Handle battery notifications."""
        try:
            if len(data) == 1:
                battery = data[0]
                if 0 <= battery <= 100:
                    self._battery = battery
                    if self._callback:
                        self._callback("battery", battery)
        except Exception:
            pass
    
    def _disconnected_callback(self, client: BleakClient) -> None:
        """Handle disconnection."""
        self.client = None
        if self._callback:
            self._callback("disconnected", None)
    
    async def async_connect(self) -> bool:
        """Connect to thermometer and enable notifications."""
        try:
            if not self.ble_device:
                self.ble_device = await BleakScanner.find_device_by_address(
                    self.address, timeout=3.0
                )
                if not self.ble_device:
                    return False
            
            self.client = BleakClient(
                self.ble_device,
                disconnected_callback=self._disconnected_callback
            )
            
            await self.client.connect(timeout=8.0)
            
            # Подписываемся на уведомления температуры
            await self.client.start_notify(
                TEMP_CHAR_UUID,
                self._temp_notification_handler
            )
            
            # Подписываемся на уведомления батареи
            await self.client.start_notify(
                BATTERY_CHAR_UUID,
                self._battery_notification_handler
            )
            
            if self._callback:
                self._callback("connected", None)
            
            return True
            
        except Exception:
            self.client = None
            return False
    
    async def async_disconnect(self) -> None:
        """Disconnect from thermometer."""
        if self.client and self.client.is_connected:
            try:
                await self.client.stop_notify(TEMP_CHAR_UUID)
                await self.client.stop_notify(BATTERY_CHAR_UUID)
                await self.client.disconnect()
            except Exception:
                pass
            finally:
                self.client = None
                if self._callback:
                    self._callback("disconnected", None)
    
    @property
    def temperature(self) -> float:
        """Current temperature (°C)."""
        return self._temperature
    
    @property
    def battery(self) -> int:
        """Current battery level (%)."""
        return self._battery
    
    @property
    def connected(self) -> bool:
        """Connection status."""
        return self.client is not None and self.client.is_connected
    
    @staticmethod
    async def discover_devices(timeout: float = 5.0) -> list[BLEDevice]:
        """Discover nearby thermometers."""
        devices = []
        
        def detection_callback(device: BLEDevice, advertisement_data):
            if advertisement_data and advertisement_data.service_uuids:
                if TEMP_SERVICE_UUID in advertisement_data.service_uuids:
                    devices.append(device)
        
        scanner = BleakScanner(detection_callback)
        await scanner.start()
        await asyncio.sleep(timeout)
        await scanner.stop()
        
        return devices
