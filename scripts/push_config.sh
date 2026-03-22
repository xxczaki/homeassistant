#!/bin/sh
cd /config

# Sync Z2M config into repo (exclude secrets and runtime files)
if [ -f /homeassistant/zigbee2mqtt/configuration.yaml ]; then
  mkdir -p zigbee2mqtt
  cp /homeassistant/zigbee2mqtt/configuration.yaml zigbee2mqtt/configuration.yaml
fi

# Sync ESPHome device configs into repo
if [ -d /homeassistant/esphome ]; then
  mkdir -p esphome
  for f in /homeassistant/esphome/*.yaml; do
    [ -f "$f" ] && cp "$f" esphome/
  done
fi

GIT_SSH_COMMAND="ssh -i /root/.ssh/ha_deploy_key -o StrictHostKeyChecking=accept-new" \
  git add -A && \
  git diff --cached --quiet || \
  git commit -m "Auto-commit from HA" && \
  git push origin main
