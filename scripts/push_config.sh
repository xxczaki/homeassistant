#!/bin/sh
cd /config
GIT_SSH_COMMAND="ssh -i /root/.ssh/ha_deploy_key -o StrictHostKeyChecking=accept-new" \
  git add -A && \
  git diff --cached --quiet || \
  git commit -m "Auto-commit from HA" && \
  git push origin main
