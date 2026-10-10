#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
sdk=${MANUS_SDK_ROOT:-$root/vendor/manus/ManusSDK_v3.1.1/ROS2/ManusSDK}
mkdir -p "$root/build"
"${CXX:-g++}" -std=c++17 -Wall -Wextra -pthread -I"$sdk/include" \
  "$root/tools/manus_probe.cpp" -L"$sdk/lib" -lManusSDK_Integrated \
  -Wl,-rpath,"$sdk/lib" -o "$root/build/manus_probe"
