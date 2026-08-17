#!/usr/bin/env bash
set -euo pipefail

# Makes an attached Thunderbolt dock's displays and USB keyboard usable before
# the root filesystem is mounted, so a clamshelled laptop can be unlocked at the
# LUKS prompt from external monitor + keyboard.
#
# Two independent things have to be true:
#
#   1. The firmware must initialise Thunderbolt pre-boot modules, otherwise the
#      dock does not exist at POST, in GRUB, or in the initramfs. On Dell this
#      is the "Enable Thunderbolt Boot Support" setting, writable from Linux
#      through dell-wmi-sysman.
#   2. The initramfs must carry a real KMS driver. Ubuntu ships GPU drivers out
#      of the initramfs and lets Plymouth render on simpledrm over the UEFI GOP
#      framebuffer, which only covers the panel the firmware lit. Without KMS
#      there is nothing driving the dock's DP outputs.
#
# Both are host-specific, so every step gates on detection and no-ops elsewhere.

SYSMAN="${SYSMAN_ROOT:-/sys/class/firmware-attributes/dell-wmi-sysman}"
TB_ATTR="ThunderboltBoot"
TB_PORTS_ATTR="ThunderboltPorts"
TB_ATTR_WANT="Enabled"
MODULES_FILE="${INITRAMFS_MODULES_FILE:-/etc/initramfs-tools/modules}"
MARK_BEGIN="# BEGIN dock-preboot-display (managed by tools/dock_preboot_display.sh)"
MARK_END="# END dock-preboot-display"
KERNEL_VERSION="${KERNEL_VERSION:-all}"

usage() {
  cat <<EOF
Usage: $0 install|status|verify-boot|remove

Enables pre-boot Thunderbolt dock display and keyboard support:
  BIOS attribute:   ${TB_ATTR}=${TB_ATTR_WANT}
  initramfs module: the boot GPU's KMS driver, added to ${MODULES_FILE}

No-ops on hosts without a Dell ${TB_ATTR} attribute or a Thunderbolt domain.
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

as_root() {
  if [ "${EUID}" -eq 0 ]; then
    "$@"
  else
    sudo "$@"
  fi
}

# --- detection ---------------------------------------------------------------

has_thunderbolt_domain() {
  [ "${DOCK_PREBOOT_FORCE:-0}" = "1" ] && return 0
  compgen -G '/sys/bus/thunderbolt/devices/domain*' >/dev/null 2>&1
}

has_sysman_attr() {
  [ -f "${SYSMAN}/attributes/${TB_ATTR}/current_value" ]
}

is_applicable_host() {
  [ "${DOCK_PREBOOT_FORCE:-0}" = "1" ] && return 0
  has_sysman_attr && has_thunderbolt_domain
}

read_attr() {
  as_root cat "${SYSMAN}/attributes/${1}/current_value" 2>/dev/null || true
}

# The boot GPU's KMS driver, discovered rather than hardcoded, so this stays
# correct on a different Intel generation or an AMD machine. simpledrm and
# builtin drivers are skipped: neither needs adding to the initramfs.
detect_kms_module() {
  local card driver

  if [ -n "${DOCK_PREBOOT_KMS_MODULE:-}" ]; then
    printf '%s\n' "${DOCK_PREBOOT_KMS_MODULE}"
    return 0
  fi

  for card in /sys/class/drm/card*; do
    [ -e "${card}/device/driver" ] || continue
    driver="$(basename "$(readlink -f "${card}/device/driver")")"

    case "${driver}" in
      simpledrm|simple-framebuffer|efi-framebuffer|vesa-framebuffer)
        continue
        ;;
    esac

    # A builtin driver is already in the kernel image; nothing to copy.
    modinfo -F filename "${driver}" >/dev/null 2>&1 || continue
    [ "$(modinfo -F filename "${driver}" 2>/dev/null)" = "(builtin)" ] && continue

    printf '%s\n' "${driver}"
    return 0
  done

  return 1
}

# --- BIOS attribute ----------------------------------------------------------

sysman_admin_password_enabled() {
  [ "$(cat "${SYSMAN}/authentication/Admin/is_enabled" 2>/dev/null || echo 0)" = "1" ]
}

set_thunderbolt_boot() {
  local current ports

  current="$(read_attr "${TB_ATTR}")"
  if [ "${current}" = "${TB_ATTR_WANT}" ]; then
    log "${TB_ATTR} is already ${TB_ATTR_WANT}"
    return 0
  fi

  ports="$(read_attr "${TB_PORTS_ATTR}")"
  if [ "${ports}" = "Disabled" ]; then
    die "${TB_ATTR} is read-only while ${TB_PORTS_ATTR}=Disabled; enable Thunderbolt support in BIOS setup first"
  fi

  if sysman_admin_password_enabled; then
    die "a BIOS admin password is set; dell-wmi-sysman needs it written to ${SYSMAN}/authentication/Admin/current_password before attributes can change. Set ${TB_ATTR}=${TB_ATTR_WANT} in BIOS setup (F2) instead."
  fi

  log "setting ${TB_ATTR}=${TB_ATTR_WANT} (was ${current:-unknown})"
  printf '%s' "${TB_ATTR_WANT}" | as_root tee "${SYSMAN}/attributes/${TB_ATTR}/current_value" >/dev/null

  current="$(read_attr "${TB_ATTR}")"
  [ "${current}" = "${TB_ATTR_WANT}" ] \
    || die "${TB_ATTR} still reads ${current:-empty} after write"

  log "${TB_ATTR}=${TB_ATTR_WANT} staged; applied on next reboot"
}

# --- initramfs ---------------------------------------------------------------

managed_block() {
  local module="$1"
  cat <<EOF
${MARK_BEGIN}
# KMS driver for the boot GPU, so Plymouth can drive the dock's DisplayPort
# outputs at the LUKS prompt instead of the firmware framebuffer.
${module}
${MARK_END}
EOF
}

strip_managed_block() {
  # Print $MODULES_FILE with any previously managed block removed.
  awk -v b="${MARK_BEGIN}" -v e="${MARK_END}" '
    $0 == b { skip = 1; next }
    $0 == e { skip = 0; next }
    !skip   { print }
  ' "${MODULES_FILE}"
}

write_modules_file() {
  # $1 is the desired full content; returns 1 when already identical.
  local desired="$1" tmp

  if [ -f "${MODULES_FILE}" ] && [ "${desired}" = "$(cat "${MODULES_FILE}")" ]; then
    return 1
  fi

  tmp="$(mktemp)"
  printf '%s\n' "${desired}" >"${tmp}"
  as_root install -o root -g root -m 0644 "${tmp}" "${MODULES_FILE}"
  rm -f "${tmp}"
  return 0
}

ensure_initramfs_module() {
  local module="$1" desired

  desired="$(printf '%s\n%s' "$(strip_managed_block)" "$(managed_block "${module}")")"

  if write_modules_file "${desired}"; then
    log "added ${module} to ${MODULES_FILE}"
    return 0
  fi

  log "${module} is already listed in ${MODULES_FILE}"
  return 1
}

rebuild_initramfs() {
  need_cmd update-initramfs
  log "rebuilding initramfs for ${KERNEL_VERSION}"
  as_root update-initramfs -u -k "${KERNEL_VERSION}"
}

initramfs_path() {
  printf '/boot/initrd.img-%s\n' "$(uname -r)"
}

# --- commands ----------------------------------------------------------------

install_support() {
  local module

  if ! is_applicable_host; then
    log "no Dell ${TB_ATTR} attribute or Thunderbolt domain found; skipping pre-boot dock support"
    return 0
  fi

  need_cmd modinfo

  set_thunderbolt_boot

  module="$(detect_kms_module)" \
    || die "could not determine a loadable KMS driver for the boot GPU; set DOCK_PREBOOT_KMS_MODULE to override"

  if ensure_initramfs_module "${module}"; then
    rebuild_initramfs
  fi

  status
}

status() {
  local module img current

  if ! is_applicable_host; then
    printf 'Applicable: no (needs a Dell %s attribute and a Thunderbolt domain)\n' "${TB_ATTR}"
    return 0
  fi

  current="$(read_attr "${TB_ATTR}")"
  printf '%s: %s (want %s)\n' "${TB_ATTR}" "${current:-unknown}" "${TB_ATTR_WANT}"
  printf '%s: %s\n' "${TB_PORTS_ATTR}" "$(read_attr "${TB_PORTS_ATTR}")"
  printf 'PreBootDma: %s\n' "$(read_attr PreBootDma)"

  if [ "$(cat "${SYSMAN}/attributes/pending_reboot" 2>/dev/null || echo 0)" = "1" ]; then
    printf 'Pending reboot: yes, BIOS changes apply on next boot\n'
  else
    printf 'Pending reboot: no\n'
  fi

  if module="$(detect_kms_module)"; then
    printf 'Boot GPU KMS driver: %s\n' "${module}"
  else
    printf 'Boot GPU KMS driver: none detected\n'
    return 0
  fi

  if grep -qxF "${module}" "${MODULES_FILE}" 2>/dev/null; then
    printf 'Listed in %s: yes\n' "${MODULES_FILE}"
  else
    printf 'Listed in %s: no\n' "${MODULES_FILE}"
  fi

  img="$(initramfs_path)"
  if [ -r "${img}" ] && command -v lsinitramfs >/dev/null 2>&1; then
    if lsinitramfs "${img}" 2>/dev/null | grep -q "/drm/${module}/${module}\.ko"; then
      printf 'Present in %s: yes\n' "${img}"
    else
      printf 'Present in %s: no, run install\n' "${img}"
    fi
  else
    printf 'Present in %s: unreadable, re-run with sudo to check\n' "${img}"
  fi
}

verify_boot() {
  local module img missing=0 fw

  if ! is_applicable_host; then
    log "not an applicable host; nothing to verify"
    return 0
  fi

  [ "$(read_attr "${TB_ATTR}")" = "${TB_ATTR_WANT}" ] \
    || { warn "${TB_ATTR} is not ${TB_ATTR_WANT}"; missing=1; }

  if module="$(detect_kms_module)"; then
    img="$(initramfs_path)"
    if [ -r "${img}" ]; then
      lsinitramfs "${img}" 2>/dev/null | grep -q "/drm/${module}/${module}\.ko" \
        || { warn "${module} is missing from ${img}"; missing=1; }

      # A KMS driver without its firmware still cannot modeset.
      for fw in $(modinfo -F firmware "${module}" 2>/dev/null); do
        if [ -e "/usr/lib/firmware/${fw}" ] || [ -e "/usr/lib/firmware/${fw}.zst" ] \
          || [ -e "/usr/lib/firmware/updates/${fw}" ]; then
          lsinitramfs "${img}" 2>/dev/null | grep -q "firmware/${fw}" \
            || warn "firmware ${fw} is on disk but missing from ${img}"
        fi
      done
    else
      warn "cannot read ${img}; re-run with sudo"
      missing=1
    fi
  else
    warn "no loadable KMS driver detected for the boot GPU"
    missing=1
  fi

  if [ "${missing}" -ne 0 ]; then
    die "pre-boot dock support is not fully in place; run install"
  fi

  log "pre-boot dock display support is in place"
}

remove_support() {
  local desired

  if [ ! -f "${MODULES_FILE}" ]; then
    log "${MODULES_FILE} does not exist; nothing to remove"
  elif ! grep -qxF "${MARK_BEGIN}" "${MODULES_FILE}"; then
    log "no managed block in ${MODULES_FILE}"
  else
    desired="$(strip_managed_block)"
    if write_modules_file "${desired}"; then
      log "removed managed block from ${MODULES_FILE}"
      rebuild_initramfs
    fi
  fi

  if is_applicable_host && [ "$(read_attr "${TB_ATTR}")" = "${TB_ATTR_WANT}" ]; then
    warn "${TB_ATTR} is still ${TB_ATTR_WANT}; reset it in BIOS setup or with:"
    warn "  printf Disabled | sudo tee ${SYSMAN}/attributes/${TB_ATTR}/current_value"
  fi
}

case "${1:-}" in
  install)
    install_support
    ;;
  status)
    status
    ;;
  verify-boot)
    verify_boot
    ;;
  remove)
    remove_support
    ;;
  -h|--help|help|"")
    usage
    ;;
  *)
    usage
    die "unknown command: $1"
    ;;
esac
