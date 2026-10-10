#!/usr/bin/env bash
set -eo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
# ROS setup scripts reference variables that may be unset under `set -u`.
set +u
source /opt/ros/jazzy/setup.bash
source "$root/ros2_ws/install/setup.bash"
set -u
exec "$root/.venv/bin/python" \
  "$root/ros2_ws/src/manus_ros2/client_scripts/manus_data_viz.py" "$@"
