#!/usr/bin/env bash
set -euo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
compose_file="$root/compose.manus.yaml"
compose=(docker compose -f "$compose_file")

die() {
  echo "docker_manus: $*" >&2
  exit 1
}

need_docker() {
  command -v docker >/dev/null 2>&1 || die "Docker Engine is not installed on the host. Install Docker and the Compose plugin first."
  docker compose version >/dev/null 2>&1 || die "Docker Compose plugin is not available. Install docker-compose-plugin first."
  if ! docker info >/dev/null 2>&1; then
    if [[ -S /var/run/docker.sock ]] && ! id -nG | tr ' ' '\n' | grep -qx docker; then
      die "Docker socket permission denied. Run 'newgrp docker' (or log out and in), then retry; alternatively prefix the command with 'sg docker -c'."
    fi
    die "Docker daemon is not reachable. Start Docker Engine and retry."
  fi
}

check_usb() {
  [[ -d /dev/bus/usb ]] || die "/dev/bus/usb is missing on the host"
  if command -v lsusb >/dev/null 2>&1; then
    lsusb -d 3325:0049 >/dev/null 2>&1 || die "MANUS dongle 3325:0049 was not found; reconnect the dongle"
  else
    echo "Warning: lsusb is unavailable; /dev/bus/usb exists but the dongle was not identified." >&2
  fi
  echo "USB path is ready."
}

usage() {
  cat <<'EOF'
Usage: tools/docker_manus.sh <command>

Commands:
  build       Build the private MANUS ROS image
  up          Check the dongle and start one publisher container
  down        Stop and remove the publisher container
  restart     Stop, then start the publisher container
  logs        Follow publisher logs
  status      Show container status and health
  check-usb   Check host USB access to the MANUS dongle
  shell       Open a shell inside the running container
  terminal    Start a foreground interactive container shell
  verify      Show glove topics and side/hand_id samples
EOF
}

command_name=${1:-}
shift || true

case "$command_name" in
  build)
    need_docker
    "${compose[@]}" build "$@"
    ;;
  up)
    need_docker
    check_usb
    "${compose[@]}" up -d --remove-orphans manus
    "${compose[@]}" ps
    ;;
  down)
    need_docker
    "${compose[@]}" down "$@"
    ;;
  restart)
    need_docker
    check_usb
    "${compose[@]}" down
    "${compose[@]}" up -d --remove-orphans manus
    "${compose[@]}" ps
    ;;
  logs)
    need_docker
    exec "${compose[@]}" logs -f --tail=100 manus "$@"
    ;;
  status)
    need_docker
    "${compose[@]}" ps
    ;;
  check-usb)
    check_usb
    ;;
  shell)
    need_docker
    exec "${compose[@]}" exec manus /bin/bash "$@"
    ;;
  terminal|interactive|run)
    need_docker
    check_usb
    running_manus_container="$("${compose[@]}" ps --status running -q manus 2>/dev/null || true)"
    [[ -z "$running_manus_container" ]] ||
      die "publisher container is already running; use 'bash tools/docker_manus.sh down' first"
    echo "Interactive MANUS container started. Run ROS commands in this terminal; type 'exit' to stop it."
    if [[ $# -eq 0 ]]; then
      exec "${compose[@]}" run --rm --no-deps --service-ports manus /bin/bash
    else
      exec "${compose[@]}" run --rm --no-deps --service-ports manus "$@"
    fi
    ;;
  verify)
    need_docker
    exec "${compose[@]}" exec -T manus /bin/bash -lc \
      'source /opt/ros/${ROS_DISTRO}/setup.bash &&
       source /work/ros2_ws/install/setup.bash &&
       ros2 topic info /manus_glove_0 || true;
       ros2 topic info /manus_glove_1 || true;
       for topic in /manus_glove_0 /manus_glove_1; do
         echo "--- ${topic} ---";
         timeout 8s ros2 topic echo "${topic}" --once 2>/dev/null |
           grep -E "glove_id:|side:|hand_id:|raw_node_count:" || true;
       done'
    ;;
  ""|-h|--help|help)
    usage
    ;;
  *)
    usage >&2
    die "unknown command: $command_name"
    ;;
esac
