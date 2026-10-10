# MANUS Linux integration

Inspected local project: `/home/jhyoon/Desktop/Hand_retargetting` (the requested spelling `hane_retargetting` was not found). Ubuntu 24.04, MANUS SDK 3.1.1, and ROS 2 packages. The official `wuji-technology/wujihandros2` Git checkout is now under `ros2_ws/src/wuji_hand`, with its official `wuji-description` submodule. No replacement WUJI driver or speculative joint mapping was added.

## Changes

- Both Linux Makefiles default to `ManusSDK_Integrated` and use executable-relative library lookup. To deliberately build Remote, clean first and build with `MANUS_LIBRARY=ManusSDK` (its external gRPC dependencies are required).
- ROS `ros2_ws/src/manus_ros2/CMakeLists.txt`: Integrated by default, explicit `MANUS_SDK_ROOT`, missing-SDK checks, Curses discovery, selected-library installation and `$ORIGIN` runtime lookup. `-DMANUS_INTEGRATED=OFF` selects Remote in both linkage and initialization.
- ROS package manifest declares native dependencies. Publisher accepts `host_ip` and positive `connection_attempts` (default 5); connection failures terminate with a nonzero exit. Any SDK connection error is rejected, an unmatched requested IP no longer falls back to another host, shutdown tolerates an absent landscape, and publication remains disabled while the required license is absent.
- Existing `manus_glove_0`, `manus_glove_1`, etc. topics and `manus_ros2_msgs/msg/ManusGlove` schema retained. Topic numbering is discovery-dependent: consumers must check `glove_id` and `side`. These vendor messages do not contain ROS timestamps; this remains a limitation for a future teleoperation consumer.
- `tools/manus_probe.cpp` provides a noninteractive Integrated startup/raw-frame/license diagnostic. It does not command the robot or vibrate gloves.
- `tools/build_probe.sh`, `tools/build_ros.sh`, `tools/ros_entrypoint.sh`: reproducible build/runtime entry points.
- `Dockerfile.manus`, `compose.manus.yaml`: ROS 2 Jazzy container by default with Integrated builds, host networking, restricted `/dev/bus/usb` access and read-only udev data. See `README.docker.md` for deployment and USB checks.
- `hardware/manus/udev/70-manus-hid.rules` and `hardware/wuji/udev/70-wuji-hand.rules`: MANUS/WUJI device IDs with plugdev/uaccess permissions. `tools/install_udev_rules.sh` installs both rules on the host.
- `hardware/wuji/`: WUJI serial/calibration/firmware notes and host hardware assets.
- `ros2_ws/src/wuji_hand/`: official `wujihandros2` Git checkout and `wuji-description` submodule. The pinned `wujihandcpp` SDK is cached under `downloads/wuji/` and installed on native hosts with `tools/install_wuji_sdk.sh`; Docker installs the same version during image build.

## Current project layout

```text
hand_retargetting/
├── vendor/manus/          # Unmodified MANUS SDK and vendor examples
├── ros2_ws/
│   └── src/               # ROS 2 packages and WUJI bridge
├── hardware/
│   ├── manus/              # MANUS host rules and notes
│   └── wuji/               # WUJI hardware assets
├── tools/                  # build, udev and visualization entry points
└── .venv/                  # shared Python environment
```

The shared `.venv` uses system site packages so it can see ROS 2 Jazzy after the ROS setup script is sourced. It now contains the Open3D dependencies that were previously isolated in `.venv_ros_viz`; that second environment has been removed.

## Native usage

From the project root:

```bash
bash tools/build_probe.sh
./build/manus_probe
source /opt/ros/jazzy/setup.bash
bash tools/build_ros.sh
source ros2_ws/install/setup.bash
ros2 run manus_ros2 manus_data_publisher --ros-args -p connection_attempts:=5
ros2 topic list
ros2 topic echo /manus_glove_0
```

The SDK writes settings under `${XDG_CONFIG_HOME:-$HOME/.config}/Manus`. This directory must be writable. The SDK also needs local sockets and USB access. For an isolated diagnostic, set `XDG_CONFIG_HOME` to a writable test directory. Use `timeout 20s ./build/manus_probe` to bound a proprietary SDK hang. Exit 0 means both a valid Integrated license and actual raw frames were observed; initialization success alone does not establish either.

Run `sudo bash tools/install_udev_rules.sh` to install both rules into `/etc/udev/rules.d/`, reload rules and reconnect devices. The desktop session receives uaccess permissions; headless users need membership in `plugdev`. Container udev access depends on the host rules and devices. Do not run multiple Core/Integrated instances concurrently.

## Container usage

```bash
bash tools/docker_manus.sh build
bash tools/docker_manus.sh up
bash tools/docker_manus.sh verify
```

For local-style, foreground container work, stop the detached service and use
the interactive terminal mode. It gives a shell in the USB-enabled container;
start `manus_data_publisher` manually there and run RViz2 from a host terminal:

```bash
bash tools/docker_manus.sh down
bash tools/docker_manus.sh terminal
```

The detailed container and USB instructions are in [README.docker.md](README.docker.md). The image includes proprietary MANUS files and the official WUJI SDK; keep it private. The image also installs the official WUJI ROS2 driver runtime dependencies.

## Validation

Passed:

- `bash tools/build_probe.sh` (G++ C++17).
- `make -C vendor/manus/ManusSDK_v3.1.1/SDKMinimalClient_Linux -j2`.
- `make -C vendor/manus/ManusSDK_v3.1.1/SDKClient_Linux -j2` (two pre-existing string-literal-to-char-pointer warnings).
- `./build/manus_probe --help`.
- Shell syntax checks on all three scripts and XML parsing of both ROS package manifests.
- `readelf` confirms the installed ROS publisher links `libManusSDK_Integrated.so` with an origin-relative runtime path.
- `bash tools/build_ros.sh -DBUILD_TESTING=OFF` succeeds with the native ROS 2 Jazzy installation.
- The live Integrated publisher discovers the wireless MANUS dongle and glove, and `/manus_glove_0` emits a real 25-node hand message.
- Docker image build completed with the official WUJI SDK 1.8.0 and all six selected ROS packages. Physical WUJI runtime was not claimed because no WUJI hand was present on the USB bus during this check.
- The official WUJI source checkout and submodule are present. The project build script includes `wujihand_msgs`, `wujihand_driver`, `wujihand_bringup` and `wuji_description` when `wujihandcpp` is installed, and otherwise skips those packages while preserving the MANUS build. End-to-end WUJI operation still requires the SDK, compatible firmware, device serials and physical hardware.

Reference: https://docs.manus-meta.com/latest/Plugins/SDK/Linux/ . Consult the bundled 3.1.1 headers for version-specific API details.

## Current runtime validation

- ROS 2 Jazzy packages build with `bash tools/build_ros.sh -DBUILD_TESTING=OFF` into `ros2_ws/build`, `ros2_ws/install` and `ros2_ws/log`.
- `/manus_glove_0` publishes `manus_ros2_msgs/msg/ManusGlove` at approximately 120 Hz.
- `manus_glove_markers` publishes `/manus_glove_markers` as `visualization_msgs/msg/MarkerArray` at approximately 120 Hz.
- RViz2 subscribes to `/manus_glove_markers` with fixed frame `manus` using `ros2 launch manus_ros2 manus_rviz.launch.py`.
- `tools/run_manus_viz.sh` starts the legacy Open3D viewer from the shared `.venv` when needed.

The host rules are installed at `/etc/udev/rules.d/70-manus-hid.rules` and
`/etc/udev/rules.d/70-wuji-hand.rules`; their project sources are under
`hardware/manus/udev/` and `hardware/wuji/udev/`. A temporary migration backup
was moved outside the project tree after the reorganization so ROS package
discovery stays unambiguous.
