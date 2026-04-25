#!/bin/sh
set -e
cd /config

# Deploy key under /config/.ssh (gitignored) is reachable from inside
# HA core's container, where shell_command runs.
export GIT_SSH_COMMAND="ssh -i /config/.ssh/ha_deploy_key -o StrictHostKeyChecking=accept-new"

# Stage the Z2M config in redacted form without touching the live file.
# /config and /homeassistant are the same mount on HA OS, so any
# in-place rewrite strips the real network_key / password that Z2M
# needs at runtime. Trick: pipe the awk-redacted bytes into
# `git hash-object -w --stdin` (writes a blob to .git/objects, prints
# its SHA) and stage that SHA at the file's path via `update-index
# --cacheinfo`. The working tree is never modified.
if [ -f zigbee2mqtt/configuration.yaml ]; then
  REDACTED_SHA=$(awk '
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
  ' zigbee2mqtt/configuration.yaml | git hash-object -w --stdin)
fi

git add -A
if [ -n "${REDACTED_SHA:-}" ]; then
  git update-index --add --cacheinfo 100644,"$REDACTED_SHA",zigbee2mqtt/configuration.yaml
fi

if ! git diff --cached --quiet; then
  git commit -m "Auto-commit from HA"
  git push origin main
fi
