#!/usr/bin/env bash
# Retired safety stub. Prod restarts are permanently disabled by policy.
set -euo pipefail
echo "resourcepack restart: BLOCKED — prod restart is disabled" >&2
exit 2
