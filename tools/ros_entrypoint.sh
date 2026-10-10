#!/usr/bin/env bash
set -e
if [[ -f /etc/profile.d/manus-ros.sh ]]; then
  # shellcheck disable=SC1091
  source /etc/profile.d/manus-ros.sh
fi
exec "$@"
