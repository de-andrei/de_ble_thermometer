"""Async Python library for Relsib WT50 Thermometer."""

import asyncio
import logging
import math
from typing import Optional, Callable, Any, Union

from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice

_LOGGER = logging.getLogger(__name__)
# Временно включаем отладку для поиска проблемы
_LOGGER.setLevel(logging.DEBUG)

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
            # Логируем сырые данные для отладки
            _LOGGER.debug(f"Raw temperature data: {data.hex()} from sender {sender}")
            
            # Проверяем размер данных
            if len(data) != 5:
                _LOGGER.warning(f"Unexpected data length: {len(data)} bytes, ignoring")
                return
            
            flags = data[0]
            fahrenheit = (flags & 0x01) == 0x01
            
            # Извлекаем мантиссу (24 бита)
            mantissa = (data[1] | (data[2] << 8) | (data[3] << 16))
            exponent = data[4]
            
            _LOGGER.debug(f"Flags: {flags:02x}, Mantissa: {mantissa}, Exponent: {exponent}")
            
            # КРИТИЧЕСКАЯ ПРОВЕРКА: если мантисса больше 10000 - это явно не температура
            if mantissa > 10000:
                _LOGGER.warning(f"Mantissa too large: {mantissa}, ignoring packet")
                return
            
            # Преобразуем exponent из signed byte
            if exponent >= 128:  # отрицательное число
                exponent = exponent - 256
            
            # Вычисляем температуру
            temperature = mantissa * math.pow(10, exponent)
            
            if fahrenheit:
                temperature = (temperature - 32) * 5.0 / 9.0
            
            # Округляем до 1 знака
            temperature = round(temperature, 1)
            
            _LOGGER.debug(f"Calculated temperature: {temperature}°C")
            
            # Проверяем разумный диапазон для температуры тела
            if 25.0 <= temperature <= 45.0:
                self._temperature = temperature
                if self._callback:
                    self._callback("temperature", temperature)
            else:
                _LOGGER.warning(f"Temperature out of range: {temperature}°C")
                    
        except Exception as e:
            _LOGGER.error(f"Error parsing temperature: {e}")
    
    def _battery_notification_handler(self, sender: int, data: bytearray) -> None:
        """Handle battery notifications."""
        try:
            _LOGGER.debug(f"Raw battery data: {data.hex()} from sender {sender}")
            
            if len(data) != 1:
                _LOGGER.warning(f"Unexpected battery data length: {len(data)} bytes")
                return
                
            battery = data[0]
            if 0 <= battery <= 100:
                self._battery = battery
                if self._callback:
                    self._callback("battery", battery)
            else:
                _LOGGER.warning(f"Battery out of range: {battery}")
                
        except Exception as e:
            _LOGGER.error(f"Error parsing battery: {e}")
    
    def _disconnected_callback(self, client: BleakClient) -> None:
        """Handle disconnection."""
        _LOGGER.debug("Device disconnected")
        self.client = None
        if self._callback:
            self._callback("disconnected", None)
    
    async def async_connect(self) -> bool:
        """Connect to thermometer and enable notifications."""
        try:
            if not self.ble_device:
                _LOGGER.debug(f"Scanning for device {self.address}")
                self.ble_device = await BleakScanner.find_device_by_address(
                    self.address, timeout=3.0
                )
                if not self.ble_device:
                    _LOGGER.debug(f"Device {self.address} not found")
                    return False
            
            _LOGGER.debug(f"Connecting to {self.address}")
            self.client = BleakClient(
                self.ble_device,
                disconnected_callback=self._disconnected_callback
            )
            
            await self.client.connect(timeout=8.0)
            _LOGGER.debug("Connected, enabling notifications")
            
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
            
        except Exception as e:
            _LOGGER.error(f"Connection error: {e}")
            self.client = None
            return False
    
    async def async_disconnect(self) -> None:
        """Disconnect from thermometer."""
        if self.client and self.client.is_connected:
            try:
                _LOGGER.debug("Disconnecting")
                await self.client.stop_notify(TEMP_CHAR_UUID)
                await self.client.stop_notify(BATTERY_CHAR_UUID)
                await self.client.disconnect()
            except Exception as e:
                _LOGGER.error(f"Disconnect error: {e}")
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
                    _LOGGER.debug(f"Found thermometer: {device.address}")
        
        scanner = BleakScanner(detection_callback)
        await scanner.start()
        await asyncio.sleep(timeout)
        await scanner.stop()
        
        return devices
