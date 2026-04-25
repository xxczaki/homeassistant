#!/bin/sh
set -e
cd /config

# All git ops below need the deploy key. The key lives at
# /config/.ssh/ha_deploy_key (gitignored) so the path is reachable
# from inside HA core's container, where shell_command runs.
# /root/.ssh/ on the supervisor host is not visible there.
export GIT_SSH_COMMAND="ssh -i /config/.ssh/ha_deploy_key -o StrictHostKeyChecking=accept-new"

# Sync Z2M config into the repo and redact secrets so they never reach
# the remote. The live file under /homeassistant keeps the real values;
# only the repo copy is scrubbed. Done with awk (not python) because the
# shell_command exec env is busybox sh and we want zero interpreter
# dependencies between cp and git add.
if [ -f /homeassistant/zigbee2mqtt/configuration.yaml ]; then
  mkdir -p zigbee2mqtt
  cp /homeassistant/zigbee2mqtt/configuration.yaml zigbee2mqtt/configuration.yaml.tmp
  awk '
    BEGIN { in_block = 0 }
    in_block && /^[[:space:]]+- / { next }
    in_block { in_block = 0 }
    /^[[:space:]]*password:[[:space:]]/ {
      match($0, /^[[:space:]]*/)
      print substr($0, 1, RLENGTH) "# password: <redacted>"
      next
    }
    /^[[:space:]]*(network_key|ext_pan_id):[[:space:]]*$/ {
      match($0, /^[[:space:]]*/)
      indent = substr($0, 1, RLENGTH)
      match($0, /(network_key|ext_pan_id)/)
      key = substr($0, RSTART, RLENGTH)
      print indent "# " key ": <redacted>"
      in_block = 1
      next
    }
    { print }
  ' zigbee2mqtt/configuration.yaml.tmp > zigbee2mqtt/configuration.yaml
  rm zigbee2mqtt/configuration.yaml.tmp
fi

# Sync ESPHome device configs into the repo
if [ -d /homeassistant/esphome ]; then
  mkdir -p esphome
  for f in /homeassistant/esphome/*.yaml; do
    [ -f "$f" ] && cp "$f" esphome/
  done
fi

git add -A
if ! git diff --cached --quiet; then
  git commit -m "Auto-commit from HA"
  git push origin main
fi
