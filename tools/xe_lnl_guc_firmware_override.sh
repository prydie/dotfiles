#!/usr/bin/env bash
set -euo pipefail

TAG="${XE_LNL_GUC_TAG:-20250613}"
VERSION="${XE_LNL_GUC_VERSION:-70.45.2}"
SHA256="${XE_LNL_GUC_SHA256:-53dfed52dda17c6e1116dbffe4506a0f1125c654750f61413bd4446be4e5d81f}"
FIRMWARE_REL="xe/lnl_guc_70.bin"
FIRMWARE_ROOT="${XE_FIRMWARE_ROOT:-/usr/lib/firmware}"
BASE_URL="${XE_LINUX_FIRMWARE_BASE_URL:-https://git.kernel.org/pub/scm/linux/kernel/git/firmware/linux-firmware.git/plain}"
KERNEL_VERSION="${KERNEL_VERSION:-all}"

OVERRIDE="${FIRMWARE_ROOT}/updates/${FIRMWARE_REL}"
PACKAGED="${FIRMWARE_ROOT}/${FIRMWARE_REL}"
PACKAGED_ZST="${PACKAGED}.zst"

usage() {
  cat <<EOF
Usage: $0 install|status|verify-boot|remove

Manages the local Lunar Lake xe GuC firmware override:
  ${OVERRIDE}

Pinned upstream source:
  tag:     ${TAG}
  version: ${VERSION}
  sha256:  ${SHA256}
EOF
}

log() {
  printf 'INFO: %s\n' "$*"
}

warn() {
  printf 'WARN: %s\n' "$*" >&2
}

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "missing required command: $1"
}

is_lunar_lake_xe_host() {
  local dev device vendor

  [ "${XE_LNL_GUC_FORCE:-0}" = "1" ] && return 0

  for dev in /sys/bus/pci/devices/*; do
    if [ ! -r "${dev}/vendor" ] || [ ! -r "${dev}/device" ]; then
      continue
    fi

    vendor="$(cat "${dev}/vendor")"
    device="$(cat "${dev}/device")"

    [ "${vendor}" = "0x8086" ] || continue
    case "${device}" in
      0x6420|0x64a0|0x64b0)
        return 0
        ;;
    esac
  done

  return 1
}

as_root() {
  if [ "${EUID}" -eq 0 ]; then
    "$@"
  else
    sudo "$@"
  fi
}

firmware_url() {
  printf '%s/%s?h=%s\n' "${BASE_URL}" "${FIRMWARE_REL}" "${TAG}"
}

whence_url() {
  printf '%s/WHENCE?h=%s\n' "${BASE_URL}" "${TAG}"
}

sha256_file() {
  sha256sum "$1" | awk '{print $1}'
}

download_verified() {
  local tmp actual whence_match
  tmp="$(mktemp -d)"

  curl -fsSL "$(firmware_url)" -o "${tmp}/lnl_guc_70.bin"
  curl -fsSL "$(whence_url)" -o "${tmp}/WHENCE"

  whence_match="Version: GuC API/APB ver ${VERSION} for Lunarlake"
  grep -F "File: ${FIRMWARE_REL}" -A1 "${tmp}/WHENCE" | grep -Fq "${whence_match}" \
    || die "upstream WHENCE for tag ${TAG} does not list ${whence_match}"

  actual="$(sha256_file "${tmp}/lnl_guc_70.bin")"
  [ "${actual}" = "${SHA256}" ] \
    || die "checksum mismatch for downloaded firmware: got ${actual}, expected ${SHA256}"

  printf '%s\n' "${tmp}/lnl_guc_70.bin"
}

rebuild_initramfs() {
  if command -v update-initramfs >/dev/null 2>&1; then
    log "rebuilding initramfs for ${KERNEL_VERSION}"
    as_root update-initramfs -u -k "${KERNEL_VERSION}"
  else
    warn "update-initramfs not found; reboot may still load firmware from ${FIRMWARE_ROOT}"
  fi
}

install_override() {
  local src
  need_cmd sha256sum
  need_cmd awk

  if ! is_lunar_lake_xe_host; then
    log "no Lunar Lake Intel graphics device found; skipping ${FIRMWARE_REL} override"
    return 0
  fi

  if [ -f "${OVERRIDE}" ] && [ "$(sha256_file "${OVERRIDE}")" = "${SHA256}" ]; then
    log "${FIRMWARE_REL} ${VERSION} override already installed"
    status
    return 0
  fi

  need_cmd curl
  need_cmd grep

  src="$(download_verified)"
  log "installing ${FIRMWARE_REL} ${VERSION} override"
  as_root install -D -o root -g root -m 0644 "${src}" "${OVERRIDE}"
  rebuild_initramfs
  status
}

status() {
  local override_sha packaged_sha

  printf 'Pinned override target: %s from linux-firmware tag %s\n' "${VERSION}" "${TAG}"
  printf 'Override path: %s\n' "${OVERRIDE}"

  if [ -f "${OVERRIDE}" ]; then
    override_sha="$(sha256_file "${OVERRIDE}")"
    printf 'Override: present sha256=%s\n' "${override_sha}"
    if [ "${override_sha}" != "${SHA256}" ]; then
      warn "override checksum differs from this script's pinned checksum"
    fi
  else
    printf 'Override: absent\n'
  fi

  if [ -f "${PACKAGED_ZST}" ] && command -v zstdcat >/dev/null 2>&1; then
    packaged_sha="$(zstdcat "${PACKAGED_ZST}" | sha256sum | awk '{print $1}')"
    printf 'Packaged firmware: %s sha256=%s\n' "${PACKAGED_ZST}" "${packaged_sha}"
    if [ "${packaged_sha}" = "${SHA256}" ]; then
      printf 'Packaged firmware matches the override; remove is now safe.\n'
    else
      printf 'Packaged firmware differs from the override; keep override unless boot logs prove it is obsolete.\n'
    fi
  elif [ -f "${PACKAGED}" ]; then
    packaged_sha="$(sha256_file "${PACKAGED}")"
    printf 'Packaged firmware: %s sha256=%s\n' "${PACKAGED}" "${packaged_sha}"
  else
    printf 'Packaged firmware: not found at %s or %s\n' "${PACKAGED}" "${PACKAGED_ZST}"
  fi
}

verify_boot() {
  need_cmd journalctl

  journalctl -k -b --no-pager | grep -E 'lnl_guc|GuC firmware|Using GuC' || true

  if journalctl -k -b --no-pager | grep -Fq "GuC firmware (${VERSION}) is recommended"; then
    die "current boot still reports that ${VERSION} is missing"
  fi

  if journalctl -k -b --no-pager | grep -F "Using GuC firmware from ${FIRMWARE_REL} version ${VERSION}" >/dev/null; then
    log "current boot is using ${FIRMWARE_REL} version ${VERSION}"
  else
    warn "current boot did not clearly report ${FIRMWARE_REL} version ${VERSION}"
  fi
}

remove_override() {
  if [ -f "${OVERRIDE}" ]; then
    log "removing ${OVERRIDE}"
    as_root rm -f "${OVERRIDE}"
    rebuild_initramfs
  else
    log "override is already absent"
  fi
}

case "${1:-}" in
  install)
    install_override
    ;;
  status)
    status
    ;;
  verify-boot)
    verify_boot
    ;;
  remove)
    remove_override
    ;;
  -h|--help|help|"")
    usage
    ;;
  *)
    usage
    die "unknown command: $1"
    ;;
esac
