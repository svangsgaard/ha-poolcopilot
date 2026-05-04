"""Constants for the Pool Copilot integration."""

DOMAIN = "poolcopilot"
CONF_API_KEY = "api_key"
CONF_SCAN_INTERVAL = "scan_interval"

# API Configuration
API_BASE_URL = "https://poolcopilot.com/api/v1"
API_TIMEOUT = 30

# Update intervals
SCAN_INTERVAL_SECONDS = 300  # 5 minutes

# Sensor types
SENSOR_TYPES = {
    "water_temperature": {
        "name": "Water Temperature",
        "unit": "°C",
        "icon": "mdi:thermometer",
        "device_class": "temperature",
        "path": ["PoolCop", "temperature", "water"],
    },
    "air_temperature": {
        "name": "Air Temperature",
        "unit": "°C",
        "icon": "mdi:thermometer",
        "device_class": "temperature",
        "path": ["PoolCop", "temperature", "air"],
    },
    "ph": {
        "name": "pH Level",
        "unit": "pH",
        "icon": "mdi:flask",
        "device_class": None,
        "path": ["PoolCop", "pH"],
    },
    "orp": {
        "name": "ORP",
        "unit": "mV",
        "icon": "mdi:water-plus",
        "device_class": "voltage",
        "path": ["PoolCop", "orp"],
    },
    "pressure": {
        "name": "Pressure",
        "unit": "kPa",
        "icon": "mdi:gauge",
        "device_class": "pressure",
        "path": ["PoolCop", "pressure"],
    },
    "pump_status": {
        "name": "Pump Status",
        "unit": None,
        "icon": "mdi:pump",
        "device_class": None,
        "path": ["PoolCop", "status", "pump"],
    },
}
