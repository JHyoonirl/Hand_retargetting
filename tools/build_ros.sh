#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
command -v colcon >/dev/null || { echo 'Missing colcon and/or ROS 2 environment' >&2; exit 2; }
: "${ROS_DISTRO:?Source your ROS 2 setup.bash first}"
sdk_root=${MANUS_SDK_ROOT:-$root/vendor/manus/ManusSDK_v3.1.1/ROS2/ManusSDK}
workspace=${HAND_ROS_WS:-$root/ros2_ws}
mkdir -p "$workspace"
cd "$workspace"
build_core() {
  colcon build --base-paths "$root/packages" --symlink-install \
    --packages-up-to manus_ros2 manus_wuji_retargeting \
    --cmake-args -DMANUS_INTEGRATED=ON -DMANUS_SDK_ROOT="$sdk_root" "$@"
}

build_wuji() {
  local -a wuji_packages=(wujihand_driver wujihand_bringup)
  if [[ $# -gt 0 ]]; then
    colcon build --base-paths "$root/packages" --symlink-install --packages-select "${wuji_packages[@]}" --cmake-args "$@"
  else
    colcon build --base-paths "$root/packages" --symlink-install --packages-select "${wuji_packages[@]}"
  fi
}

build_core "$@"

if [[ -n "${WUJIHANDPY_SOURCE_DIR:-}" \
   || -e /usr/lib/libwujihandcpp.so \
   || -e /usr/lib/x86_64-linux-gnu/libwujihandcpp.so \
   || "$(ldconfig -p 2>/dev/null | grep -c 'libwujihandcpp\.so' || true)" -gt 0 ]]; then
  build_wuji "$@"
else
  echo "WUJI SDK not found; skipping the hardware driver and bringup packages. Install wujihandcpp to build them." >&2
fi
