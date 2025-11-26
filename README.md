# Pool Copilot Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

A custom Home Assistant integration for [Pool Copilot](https://poolcopilot.com) that allows you to monitor and control your pool equipment.

## Features

- Monitor pool water temperature
- Track pH levels
- Monitor chlorine levels (ppm)
- Track ORP (Oxidation-Reduction Potential)
- Automatic updates every 5 minutes
- Easy configuration through Home Assistant UI

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click on "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add this repository URL: `https://github.com/svangsgaard/ha-poolcopilot`
6. Select category: "Integration"
7. Click "Add"
8. Find "Pool Copilot" in the list and click "Install"
9. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/poolcopilot` directory to your Home Assistant `custom_components` directory
2. Restart Home Assistant

## Configuration

1. Go to Settings → Devices & Services
2. Click "+ Add Integration"
3. Search for "Pool Copilot"
4. Enter your Pool Copilot API key
5. Click "Submit"

### Getting Your API Key

1. Log in to your Pool Copilot account at [poolcopilot.com](https://poolcopilot.com)
2. Navigate to Settings → API
3. Generate or copy your API key

## Sensors

The integration creates the following sensors:

- `sensor.water_temperature` - Current pool water temperature (°C)
- `sensor.air_temperature` - Current air temperature (°C)
- `sensor.ph_level` - Current pH level
- `sensor.orp` - Current ORP level (mV)
- `sensor.pressure` - Filter pressure (kPa)
- `sensor.pump_status` - Pump on/off status

## Switches

The integration creates the following switches:

- `switch.pump` - Turn the pool pump on or off
- `switch.<aux_label>` - Control auxiliary outputs (aux1-aux6)
  - Automatically discovered based on your PoolCop configuration
  - Named using the label from your PoolCop settings
  - Includes attributes like slave mode, heating setpoint, and active days

## Select Entities

The integration creates the following select entities:

- `select.pump_speed` - Control pump speed (Off, Speed 1, Speed 2, Speed 3)
  - Only created if your pump has multiple speeds configured
  - Automatically detected from your PoolCop settings

## Example Automations

### Alert when pH is too high

```yaml
automation:
  - alias: "Alert when pH is too high"
    trigger:
      - platform: numeric_state
        entity_id: sensor.ph_level
        above: 7.8
    action:
      - service: notify.mobile_app
        data:
          title: "Pool pH Alert"
          message: "Pool pH is too high: {{ states('sensor.ph_level') }}"
```

### Turn pump on at sunrise

```yaml
automation:
  - alias: "Start pool pump at sunrise"
    trigger:
      - platform: sun
        event: sunrise
    action:
      - service: switch.turn_on
        target:
          entity_id: switch.pump
```

### Turn on pool lights at sunset

```yaml
automation:
  - alias: "Pool lights on at sunset"
    trigger:
      - platform: sun
        event: sunset
        offset: "-00:30:00"
    action:
      - service: switch.turn_on
        target:
          entity_id: switch.pool_light
```

### Set pump to high speed during the day

```yaml
automation:
  - alias: "High speed pump during day"
    trigger:
      - platform: time
        at: "10:00:00"
    action:
      - service: select.select_option
        target:
          entity_id: select.pump_speed
        data:
          option: "Speed 3"

## Support

For issues, feature requests, or questions:
- GitHub Issues: [github.com/svangsgaard/ha-poolcopilot/issues](https://github.com/svangsgaard/ha-poolcopilot/issues)

## License

This project is licensed under the MIT License.
