#!/bin/sh
cd /config

# Sync Z2M config into repo, then redact secrets so they never reach the
# remote. The live file keeps the real values; only the repo copy is
# scrubbed.
if [ -f /homeassistant/zigbee2mqtt/configuration.yaml ]; then
  mkdir -p zigbee2mqtt
  cp /homeassistant/zigbee2mqtt/configuration.yaml zigbee2mqtt/configuration.yaml
  python3 - <<'PY'
import re, pathlib
p = pathlib.Path("zigbee2mqtt/configuration.yaml")
text = p.read_text()
# Scalar secret on a single line: replace the value with <redacted>.
# `user: addons` is intentionally not redacted – it's the standard HA
# add-on username, not a secret.
text = re.sub(
    r"^(\s*)password:\s*.+$",
    lambda m: f"{m.group(1)}# password: <redacted>",
    text,
    flags=re.MULTILINE,
)
# Block-form secrets: `network_key:` / `ext_pan_id:` followed by an
# inline list or a multi-line YAML list. Drop the list and replace with
# a commented-out redacted placeholder.
text = re.sub(
    r"^(\s*)(network_key|ext_pan_id):\s*(?:\[[^\]]*\]|\n(?:\1\s+- [^\n]*\n)+)",
    lambda m: f"{m.group(1)}# {m.group(2)}: <redacted>\n",
    text,
    flags=re.MULTILINE,
)
p.write_text(text)
PY
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
