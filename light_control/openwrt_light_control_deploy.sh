#!/usr/bin/env bash
set -euo pipefail

# --- НАСТРОЙКИ ---
ROUTER_IP="${ROUTER_IP:-192.168.1.1}"
ROUTER_USER="${ROUTER_USER:-root}"

BASE_DIR="${OPENWRT_SDK:-$HOME/Projects/light/light_control/externals/openwrt}"
IPK_DIR="${BASE_DIR}/bin/packages/mips_24kc"

if [[ ! -d "$BASE_DIR" ]]; then
  echo "Ошибка: SDK не найден: $BASE_DIR" >&2
  exit 1
fi

DAEMON_IPK="$(find "$IPK_DIR" -name 'light_control_*.ipk' | sort | tail -n 1 || true)"
LUCI_IPK="$(find "$IPK_DIR" -name 'luci-app-light-control_*.ipk' | sort | tail -n 1 || true)"

if [[ -z "$DAEMON_IPK" ]]; then
  echo "Ошибка: light_control_*.ipk не найден в $IPK_DIR" >&2
  echo "Сначала запусти сборку: ./openwrt_light_control_build.sh" >&2
  exit 1
fi
if [[ -z "$LUCI_IPK" ]]; then
  echo "Ошибка: luci-app-light-control_*.ipk не найден в $IPK_DIR" >&2
  echo "Сначала запусти сборку: ./openwrt_light_control_build.sh" >&2
  exit 1
fi

echo "=== Деплой на роутер ($ROUTER_IP) ==="
echo "Демон: $DAEMON_IPK"
echo "LuCI:  $LUCI_IPK"

DAEMON_NAME="$(basename "$DAEMON_IPK")"
LUCI_NAME="$(basename "$LUCI_IPK")"

tar czf - -C "$(dirname "$DAEMON_IPK")" "$DAEMON_NAME" \
  -C "$(dirname "$LUCI_IPK")" "$LUCI_NAME" \
  | ssh "${ROUTER_USER}@${ROUTER_IP}" 'cat > /tmp/light_control.tar.gz'

ssh "${ROUTER_USER}@${ROUTER_IP}" \
  "cd /tmp && tar xzf light_control.tar.gz && opkg install --force-reinstall ${DAEMON_NAME} ${LUCI_NAME} && /etc/init.d/light_control restart && /etc/init.d/rpcd restart"

echo "=== Готово ==="
