#!/usr/bin/env bash
set -euo pipefail
# Run INSIDE the image guest only. Explicit script + pinned digest, no downloads.
if [[ $# -ne 2 ]]; then
  echo 'Usage: sudo bash Prepare-Omarchy.sh /path/to/vtoyboot.sh EXPECTED_SHA256' >&2
  exit 2
fi
[[ $EUID -eq 0 ]] || { echo 'Run as root inside the image guest' >&2; exit 2; }
script=$(realpath -- "$1")
[[ -f "$script" && "$2" =~ ^[a-fA-F0-9]{64}$ ]] || exit 2
actual=$(sha256sum -- "$script")
[[ "${actual%% *}" == "${2,,}" ]] || { echo 'SHA256 mismatch' >&2; exit 2; }
log="/var/log/osharbor-vtoyboot-$(date -u +%Y%m%dT%H%M%SZ).log"
{
  date -u
  uname -a
  cat /etc/os-release
  findmnt /
  lsblk -f
  cd -- "$(dirname -- "$script")"
  bash -- "$script"
} 2>&1 | tee "$log"
sync
echo "Preparation finished; boot is still pending. Log: $log"
