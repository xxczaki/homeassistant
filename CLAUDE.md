# Home Assistant Configuration

## Infrastructure

- **Home Assistant OS** accessible via `ssh root@homeassistant.local`
- **Zigbee2MQTT** addon (`45df7312_zigbee2mqtt`) manages all Zigbee devices
- **Mosquitto** MQTT broker (`core_mosquitto`) bridges Z2M to HA
- Z2M frontend is on port 8099
- Z2M config: `/config/zigbee2mqtt/configuration.yaml`
- Z2M device database: `/config/zigbee2mqtt/database.db`
- HA entity registry: `/config/.storage/core.entity_registry`
- `/config/` and `/homeassistant/` are the same mount on HA OS

## Git Sync

- A git pull addon syncs this repo to HA on startup
- `scripts/push_config.sh` auto-commits HA config changes (uses `git add -A`)
- The `.gitignore` must cover all runtime/generated files to prevent push_config.sh from committing junk
- Secrets in Z2M config are redacted in the repo (`# password: <redacted>`) but present on the live system – do NOT overwrite the live config with the repo version directly

## Critical Rules

### NEVER restart Mosquitto unless absolutely necessary

Restarting the MQTT broker (`core_mosquitto`) while Zigbee2MQTT is running will kill Z2M's MQTT connection mid-operation, which can corrupt the Z2M device database (`database.db`). If Z2M needs restarting, restart ONLY Z2M – never Mosquitto alongside it.

### NEVER use `git reset --hard` on the HA instance without checking consequences

The live HA config contains secrets (MQTT passwords, network keys) that are redacted in the repo. A hard reset will overwrite them. If you need to sync, use `git pull` or selectively checkout files.

### Entity ID renames require coordination

Renaming Zigbee devices involves three systems that must be updated in order:

1. Z2M `configuration.yaml` (friendly_name) – then restart Z2M
2. Wait for Z2M to republish MQTT discovery configs
3. HA entity registry (`core.entity_registry`) – then restart HA core
   If HA core is restarted before Z2M republishes, entities go unavailable. Always restart Z2M first, wait, then restart HA core.

## Addon Commands

```sh
ha apps restart 45df7312_zigbee2mqtt   # Restart Z2M
ha apps logs 45df7312_zigbee2mqtt      # Z2M logs
ha core restart                        # Restart HA core
```

## File Layout

- `automations.yaml` – HA automations
- `ui-lovelace.yaml` – Dashboard (Lovelace) config
- `zigbee2mqtt/configuration.yaml` – Z2M config (secrets redacted in repo)
- `esphome/` – ESPHome device configs
- `scripts/push_config.sh` – Auto-commit script for HA

## Style

- Use en dashes (–), never em dashes (—)
