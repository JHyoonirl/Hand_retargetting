#!/usr/bin/env bash
set -euo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)

usage() {
  cat <<'EOF'
Usage: tools/manus_calibrate.sh [--help]

Launch the official MANUS Linux SDK client in Core Integrated mode so the
interactive glove calibration menu can be used.

The client is taken from MANUS_SDK_CLIENT_ROOT when set, otherwise from the
vendored project copy. The Downloads copy is used only when the project copy
is unavailable.

Before starting, stop the ROS publisher and any Docker MANUS container. The
SDK client and another Core Integrated client cannot own the dongle together.
EOF
}

die() {
  echo "manus_calibrate: $*" >&2
  exit 1
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ $# -ne 0 ]]; then
  usage >&2
  die "unknown argument: $1"
fi

downloads_client="${HOME}/Downloads/MANUS_Core_3.1.1_SDK/ManusSDK_v3.1.1/SDKClient_Linux"
vendored_client="$root/vendor/manus/ManusSDK_v3.1.1/SDKClient_Linux"
client_root="${MANUS_SDK_CLIENT_ROOT:-}"

if [[ -z "$client_root" ]]; then
  if [[ -d "$vendored_client" ]]; then
    client_root="$vendored_client"
  else
    client_root="$downloads_client"
  fi
fi

[[ -d "$client_root" ]] || die "SDK client directory not found: $client_root"
library_dir="$client_root/ManusSDK/lib"
integrated_library="$library_dir/libManusSDK_Integrated.so"
client_binary="$client_root/SDKClient_Linux.out"

[[ -f "$integrated_library" ]] || die "Core Integrated library not found: $integrated_library"

if [[ ! -x "$client_binary" ]]; then
  command -v make >/dev/null 2>&1 || die "make is required to build the SDK client"
  command -v g++ >/dev/null 2>&1 || die "g++ is required to build the SDK client"
  [[ -f "$client_root/Makefile" ]] || die "SDK client is not built and has no Makefile: $client_root"

  echo "Building the MANUS Linux SDK client with Core Integrated support..."
  make -C "$client_root" \
    LDFLAGS='-L./ManusSDK/lib -lManusSDK_Integrated -lncurses -lpthread -Wl,-rpath=./ManusSDK/lib'
fi

[[ -x "$client_binary" ]] || die "SDK client build did not produce an executable: $client_binary"

publisher_pattern="$root/ros2_ws/install/manus_ros2/lib/manus_ros2/manus_data_publisher"
if pgrep -f -- "$publisher_pattern" >/dev/null 2>&1; then
  die "ROS publisher is running. Stop it first with: pkill -INT -f '$publisher_pattern'"
fi

if command -v docker >/dev/null 2>&1; then
  running_manus_container="$(docker compose -f "$root/compose.manus.yaml" ps --status running --services 2>/dev/null || true)"
  if grep -qx 'manus' <<<"$running_manus_container"; then
    die "Docker MANUS container is running. Stop it first with: bash tools/docker_manus.sh down"
  fi
fi

if pgrep -f -- 'SDKClient_Linux\.out' >/dev/null 2>&1; then
  die "another MANUS SDK client is already running; close it before calibration"
fi

if command -v lsusb >/dev/null 2>&1 && ! lsusb -d 3325:0049 >/dev/null 2>&1; then
  echo "Warning: MANUS dongle 3325:0049 was not found by lsusb. Continuing so the SDK can report the exact device/license state." >&2
fi

cat <<'EOF'
MANUS calibration client is starting.
Select [1] Core Integrated at the first prompt.
In Main Menu press [C] for Glove Calibration.
EOF

cd "$client_root"
export LD_LIBRARY_PATH="$library_dir${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
exec "$client_binary"
