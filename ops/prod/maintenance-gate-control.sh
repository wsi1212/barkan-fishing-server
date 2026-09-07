#!/usr/bin/env bash
# Temporarily route public Minecraft traffic to the local maintenance responder.
# This script is intentionally run as root by systemd's mcserver ExecStopPre.
set -euo pipefail

ACTION="${1:?usage: maintenance-gate-control.sh <enable|disable|status>}"
TABLE=nat
CHAIN=BARKAN_MAINTENANCE_GATE
PORT=25565
GATE_PORT=25566
STATE_DIR=/run/barkan-maintenance-gate
STATE_FILE="$STATE_DIR/state"
LOCK=/run/barkan-maintenance-gate.lock
IPTABLES=${IPTABLES:-/usr/sbin/iptables}

[ "$(id -u)" = 0 ] || { echo "must run as root" >&2; exit 1; }
mkdir -p "$STATE_DIR"

ensure_chain() {
  "$IPTABLES" -w -t "$TABLE" -N "$CHAIN" 2>/dev/null || true
  "$IPTABLES" -w -t "$TABLE" -F "$CHAIN"
  "$IPTABLES" -w -t "$TABLE" -A "$CHAIN" -p tcp --dport "$PORT" -j REDIRECT --to-ports "$GATE_PORT"
  "$IPTABLES" -w -t "$TABLE" -C PREROUTING -p tcp --dport "$PORT" -j "$CHAIN" 2>/dev/null || \
    "$IPTABLES" -w -t "$TABLE" -I PREROUTING 1 -p tcp --dport "$PORT" -j "$CHAIN"
  # REDIRECT changes the destination before the INPUT chain.  Permit only this
  # internal destination; the responder itself binds loopback, never :25566.
  "$IPTABLES" -w -C INPUT -p tcp --dport "$GATE_PORT" -j ACCEPT 2>/dev/null || \
    "$IPTABLES" -w -I INPUT 1 -p tcp --dport "$GATE_PORT" -j ACCEPT
}

remove_chain() {
  while "$IPTABLES" -w -t "$TABLE" -D PREROUTING -p tcp --dport "$PORT" -j "$CHAIN" 2>/dev/null; do :; done
  "$IPTABLES" -w -t "$TABLE" -F "$CHAIN" 2>/dev/null || true
  "$IPTABLES" -w -t "$TABLE" -X "$CHAIN" 2>/dev/null || true
  while "$IPTABLES" -w -D INPUT -p tcp --dport "$GATE_PORT" -j ACCEPT 2>/dev/null; do :; done
}

exec 9>"$LOCK"
flock -x 9
case "$ACTION" in
  enable)
    ensure_chain
    printf 'arming\n' > "$STATE_FILE"
    ;;
  disable)
    remove_chain
    rm -f "$STATE_FILE"
    ;;
  status)
    if [ -f "$STATE_FILE" ]; then
      printf 'active (%s)\n' "$(tr -d '\n' < "$STATE_FILE")"
    else
      printf 'inactive\n'
    fi
    ;;
  *)
    echo "unknown action: $ACTION" >&2
    exit 2
    ;;
esac
