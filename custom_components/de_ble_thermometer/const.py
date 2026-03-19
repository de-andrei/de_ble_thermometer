"""Constants for DE BLE Thermometer integration."""
from datetime import timedelta

DOMAIN = "de_ble_thermometer"

# Device info
DEVICE_MANUFACTURER = "Relsib"
DEVICE_MODEL = "WT50"

# Service UUIDs
TEMP_SERVICE_UUID = "00001809-0000-1000-8000-00805f9b34fb"  # Health Thermometer
TEMP_CHAR_UUID = "00002a1e-0000-1000-8000-00805f9b34fb"     # Temperature Measurement

BATTERY_SERVICE_UUID = "0000180f-0000-1000-8000-00805f9b34fb"  # Battery Service
BATTERY_CHAR_UUID = "00002a19-0000-1000-8000-00805f9b34fb"     # Battery Level

# Update intervals
SCAN_INTERVAL = timedelta(seconds=30)
CONNECT_TIMEOUT = 10
BLOCK_DURATION = 210000  # 3.5 minutes in milliseconds
