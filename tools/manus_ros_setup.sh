#!/usr/bin/env bash

# Shared ROS setup for the MANUS container. This file is sourced by the
# container entrypoint and by interactive Bash shells; it is not executed on
# the host.
ros_distro="${ROS_DISTRO:-jazzy}"
ros_setup="/opt/ros/${ros_distro}/setup.bash"
workspace_setup="/work/ros2_ws/install/setup.bash"

if [[ -f "$ros_setup" ]]; then
  # shellcheck disable=SC1090
  source "$ros_setup"
fi

if [[ -f "$workspace_setup" ]]; then
  # shellcheck disable=SC1090
  source "$workspace_setup"
fi
