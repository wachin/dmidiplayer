#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
DESKTOP_SOURCE="${REPO_ROOT}/dmidiplayer/org.dmidiplayer.dmidiplayer.desktop"
LAUNCHER_PATH="${REPO_ROOT}/dmidiplayer/dmidiplayer-py"
ICON_SOURCE_DIR="${REPO_ROOT}/dmidiplayer/icons"
MIME_SOURCE="${REPO_ROOT}/dmidiplayer/org.dmidiplayer.dmidiplayer.mime.xml"

APPLICATIONS_DIR="${XDG_DATA_HOME:-${HOME}/.local/share}/applications"
ICONS_ROOT="${XDG_DATA_HOME:-${HOME}/.local/share}/icons/hicolor"
DESKTOP_TARGET="${APPLICATIONS_DIR}/org.dmidiplayer.dmidiplayer.desktop"
MIME_ROOT="${XDG_DATA_HOME:-${HOME}/.local/share}/mime"
MIME_PACKAGES_DIR="${MIME_ROOT}/packages"

mkdir -p "${APPLICATIONS_DIR}"

sed "s|^Exec=.*|Exec=${LAUNCHER_PATH} %F|" "${DESKTOP_SOURCE}" > "${DESKTOP_TARGET}"

install_icon() {
    local source_name="$1"
    local size_dir="$2"
    local target_dir="${ICONS_ROOT}/${size_dir}/apps"
    mkdir -p "${target_dir}"
    install -m 0644 "${ICON_SOURCE_DIR}/${source_name}" "${target_dir}/dmidiplayer.png"
}

install_icon "dmidiplayer_24x24.png" "24x24"
install_icon "dmidiplayer_32x32.png" "32x32"
install_icon "dmidiplayer_48x48.png" "48x48"
install_icon "dmidiplayer_64x64.png" "64x64"
install_icon "dmidiplayer_128x128.png" "128x128"
install_icon "dmidiplayer_512.png" "512x512"

if command -v desktop-file-validate >/dev/null 2>&1; then
    desktop-file-validate "${DESKTOP_TARGET}"
fi

mkdir -p "${MIME_PACKAGES_DIR}"
install -m 0644 "${MIME_SOURCE}" "${MIME_PACKAGES_DIR}/org.dmidiplayer.dmidiplayer.xml"
if command -v update-mime-database >/dev/null 2>&1; then
    update-mime-database "${MIME_ROOT}" >/dev/null 2>&1 || true
fi

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "${APPLICATIONS_DIR}" >/dev/null 2>&1 || true
fi

printf 'Installed desktop entry to %s\n' "${DESKTOP_TARGET}"
printf 'Installed icons under %s\n' "${ICONS_ROOT}"
printf 'Installed MIME types under %s\n' "${MIME_ROOT}"
