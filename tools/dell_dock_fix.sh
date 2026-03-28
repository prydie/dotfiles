#!/bin/bash
set -euo pipefail

TAG="dell-dock-fix"
STATE_DIR="/run/${TAG}"
UNBIND_STATE_FILE="${STATE_DIR}/r8152-bind-ids"

log() {
  logger -t "${TAG}" -- "$*"
}

ensure_state_dir() {
  install -m 0755 -d "${STATE_DIR}"
}

iter_r8152_ifaces() {
  local path iface driver
  for path in /sys/class/net/*; do
    [ -e "${path}" ] || continue
    iface="${path##*/}"
    driver="$(readlink -f "${path}/device/driver" 2>/dev/null || true)"
    if [ "${driver##*/}" = "r8152" ]; then
      printf '%s\n' "${iface}"
    fi
  done
}

iter_r8152_bind_ids() {
  local path
  for path in /sys/bus/usb/drivers/r8152/*:*; do
    [ -e "${path}" ] || continue
    basename "${path}"
  done
}

apply_iface_tuning() {
  local iface="${1}"

  if ! ip link show dev "${iface}" >/dev/null 2>&1; then
    log "skip tuning for missing interface ${iface}"
    return 0
  fi

  /usr/sbin/ethtool --set-eee "${iface}" eee off >/dev/null 2>&1 || true
  /usr/sbin/ethtool -A "${iface}" rx off tx off >/dev/null 2>&1 || true
  /usr/sbin/ethtool -s "${iface}" wol d >/dev/null 2>&1 || true
  log "applied EEE/flow-control/WoL mitigations to ${iface}"
}

disconnect_iface() {
  local iface="${1}"

  if command -v nmcli >/dev/null 2>&1; then
    nmcli device disconnect "${iface}" >/dev/null 2>&1 || true
  fi
  ip link set dev "${iface}" down >/dev/null 2>&1 || true
  log "forced ${iface} down before sleep"
}

pre_sleep() {
  local iface bind_id saw_iface=0 saw_bind=0

  ensure_state_dir
  : > "${UNBIND_STATE_FILE}"

  while IFS= read -r iface; do
    saw_iface=1
    apply_iface_tuning "${iface}"
    disconnect_iface "${iface}"
  done < <(iter_r8152_ifaces)

  while IFS= read -r bind_id; do
    saw_bind=1
    printf '%s\n' "${bind_id}" >> "${UNBIND_STATE_FILE}"
    printf '%s' "${bind_id}" > /sys/bus/usb/drivers/r8152/unbind
    log "unbound ${bind_id} before sleep"
  done < <(iter_r8152_bind_ids)

  if [ "${saw_iface}" -eq 0 ] && [ "${saw_bind}" -eq 0 ]; then
    log "no active r8152 dock NIC found before sleep"
  fi
}

post_sleep() {
  local bind_id iface rebound=0

  ensure_state_dir

  if [ -f "${UNBIND_STATE_FILE}" ]; then
    while IFS= read -r bind_id; do
      [ -n "${bind_id}" ] || continue
      printf '%s' "${bind_id}" > /sys/bus/usb/drivers/r8152/bind
      rebound=1
      log "rebound ${bind_id} after sleep"
    done < "${UNBIND_STATE_FILE}"
    rm -f "${UNBIND_STATE_FILE}"
  fi

  if [ "${rebound}" -eq 1 ] && command -v udevadm >/dev/null 2>&1; then
    udevadm settle >/dev/null 2>&1 || true
    sleep 2
  fi

  while IFS= read -r iface; do
    apply_iface_tuning "${iface}"
  done < <(iter_r8152_ifaces)
}

apply() {
  local iface="${1:-}"

  if [ -n "${iface}" ]; then
    apply_iface_tuning "${iface}"
    return 0
  fi

  while IFS= read -r iface; do
    apply_iface_tuning "${iface}"
  done < <(iter_r8152_ifaces)
}

case "${1:-}" in
  apply)
    apply "${2:-}"
    ;;
  pre-sleep)
    pre_sleep
    ;;
  post-sleep)
    post_sleep
    ;;
  *)
    echo "Usage: $0 {apply [iface]|pre-sleep|post-sleep}" >&2
    exit 1
    ;;
esac
