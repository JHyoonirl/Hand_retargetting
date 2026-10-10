#!/usr/bin/env bash
set -euo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
manus_rule="$root/hardware/manus/udev/70-manus-hid.rules"
wuji_rule="$root/hardware/wuji/udev/70-wuji-hand.rules"
manus_target=/etc/udev/rules.d/70-manus-hid.rules
wuji_target=/etc/udev/rules.d/70-wuji-hand.rules

[[ -f "$manus_rule" ]] || { echo "Missing rule: $manus_rule" >&2; exit 2; }
[[ -f "$wuji_rule" ]] || { echo "Missing rule: $wuji_rule" >&2; exit 2; }
sudo install -m 0644 "$manus_rule" "$manus_target"
sudo install -m 0644 "$wuji_rule" "$wuji_target"
sudo udevadm control --reload-rules
sudo udevadm trigger
echo "Installed $manus_target and $wuji_target; reconnect MANUS/WUJI devices if they were already plugged in."
