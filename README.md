# Bluetti BT - EL300

This fork of
[Patrick762/hassio-bluetti-bt](https://github.com/Patrick762/hassio-bluetti-bt)
adds persistent support for the Bluetti Elite 300 (EL300).

The fork includes:

- EL300 device registration and validated register mappings
- encrypted BLE polling support
- encrypted BLE writes for AC/DC outputs and supported settings
- Home Assistant Bluetooth adapter and ESPHome Bluetooth proxy routing
- cleanup of stale Bluetooth connections after failed polls
- encryption state reset after failed handshakes

## Installation with HACS

1. Open HACS.
2. Select **Integrations**.
3. Open the menu and select **Custom repositories**.
4. Add `https://github.com/suiciety/hassio-bluetti-bt` as an
   **Integration** repository.
5. Install **Bluetti BT - EL300** and restart Home Assistant.

Remove the upstream Bluetti BT custom repository first if HACS reports a
duplicate integration. Existing `bluetti_bt` devices and entity IDs are
preserved because this fork uses the same integration domain.

## Upstream project

The original project documentation follows.

# hassio-bluetti-bt
[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg)](https://github.com/hacs/integration)
[![Validate with hassfest](https://github.com/Patrick762/hassio-bluetti-bt/actions/workflows/hassfest_validation.yml/badge.svg)](https://github.com/Patrick762/hassio-bluetti-bt/actions/workflows/hassfest_validation.yml)
[![HACS Action](https://github.com/Patrick762/hassio-bluetti-bt/actions/workflows/HACS.yml/badge.svg)](https://github.com/Patrick762/hassio-bluetti-bt/actions/workflows/HACS.yml)

Bluetti Integration for Home Assistant

The current [Roadmap for this project and the library can be found here](https://github.com/users/Patrick762/projects/4)

## Disclaimer
This integration is provided without any warranty or support by Bluetti. I do not take responsibility for any problems it may cause in all cases. Use it at your own risk.

## Installation
To install this integration, you first need [HACS](https://hacs.xyz/) installed.
After the installation, you can use this button to install the integration:

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Patrick762&repository=hassio-bluetti-bt&category=integration)

### Supported devices:

See [bluetti-bt-lib](https://github.com/Patrick762/bluetti-bt-lib?tab=readme-ov-file#supported-powerstations-and-data)

### Available controls:
See [bluetti-bt-lib](https://github.com/Patrick762/bluetti-bt-lib?tab=readme-ov-file#supported-powerstations-and-data)

### Adding devices or fields

Please use the issue template at [bluetti-bt-lib](https://github.com/Patrick762/bluetti-bt-lib?tab=readme-ov-file#supported-powerstations-and-data)
