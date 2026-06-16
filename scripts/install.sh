#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/vbus-friwa-gateway}"
CONFIG_DIR="${CONFIG_DIR:-/etc/vbus-friwa-gateway}"
SERVICE_USER="${SERVICE_USER:-vbus-friwa}"

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Please run as root." >&2
  exit 1
fi

command -v node >/dev/null || { echo "Node.js is required." >&2; exit 1; }
command -v npm >/dev/null || { echo "npm is required." >&2; exit 1; }
command -v tar >/dev/null || { echo "tar is required." >&2; exit 1; }

if ! id "$SERVICE_USER" >/dev/null 2>&1; then
  useradd --system --no-create-home --groups dialout "$SERVICE_USER"
fi

mkdir -p "$APP_DIR" "$CONFIG_DIR"
tar --exclude='./node_modules' --exclude='./dist' -cf - . | tar -C "$APP_DIR" -xf -

cd "$APP_DIR"
npm ci
npm run build
npm prune --omit=dev

if [[ ! -f "$CONFIG_DIR/config.json" ]]; then
  cp config/example.json "$CONFIG_DIR/config.json"
fi

cp systemd/vbus-friwa-gateway.service /etc/systemd/system/vbus-friwa-gateway.service
systemctl daemon-reload

echo "Installed to $APP_DIR"
echo "Config: $CONFIG_DIR/config.json"
echo "Enable/start manually with:"
echo "  systemctl enable --now vbus-friwa-gateway.service"
