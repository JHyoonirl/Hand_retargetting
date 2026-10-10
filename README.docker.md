# Docker deployment for MANUS + ROS 2

This image runs the MANUS Core Integrated ROS 2 publisher in a container and
passes the Linux USB dongle through from the host. The MANUS SDK and its license
remain proprietary, so keep the image and registry private.

The recommended deployment is:

```text
MANUS dongle -- USB -- host udev -- Docker container -- ROS 2 topics
                                                   \-- host RViz2 (optional)
```

The container runs the publisher. RViz2 is easiest to run on the host because
it needs the host display and GPU. The ROS graph uses host networking, so host
RViz2 can subscribe to the container topics.

## Requirements

- Linux host with Docker Engine and the Docker Compose plugin
- MANUS SDK files under `vendor/manus/ManusSDK_v3.1.1/ROS2/ManusSDK`
- A MANUS dongle with the SDK component license
- The project MANUS/WUJI udev rules installed on the host

The account running these commands must be allowed to access Docker's Unix
socket. If `docker:x:...:<your-user>` is already present but the current
terminal still reports `permission denied`, refresh the group in a new shell:

```bash
newgrp docker
id -nG | tr ' ' '\n' | grep '^docker$'
```

Alternatively, run one command with the group applied without logging out:

```bash
sg docker -c 'bash tools/docker_manus.sh terminal'
```

The Dockerfile does not install Docker inside a container. Docker Engine must
run on the host.

Verify the host installation:

```bash
docker --version
docker compose version
```

## First-time USB setup

From the project root, install the MANUS and WUJI host rules, then reconnect the
devices:

```bash
sudo bash tools/install_udev_rules.sh
lsusb -d 3325:0049
lsusb -d 0483:2000
```

The current MANUS Sensor Dongle is exposed as USB vendor/product `3325:0049`.
The WUJI hand is exposed as `0483:2000`.
The Compose service passes only `/dev/bus/usb` and the read-only udev database,
and grants the USB character-device major `189` to the container. This is more
restricted than passing the entire host `/dev` tree. The host udev rules must be
installed before the devices are connected.

## Build and run

Use the wrapper script so the service name and Compose file stay consistent:

```bash
bash tools/docker_manus.sh build
bash tools/docker_manus.sh up
bash tools/docker_manus.sh logs
```

The `up` command checks for the dongle and starts one container named
`manus-retargetting`. It is safe to run again after a failure.

## Interactive terminal mode

`up` is a detached service mode: it immediately returns to the host shell and
the container runs the publisher from its Compose command. If you want to work
inside the container the same way as a local terminal, stop the detached
publisher and start the foreground terminal mode instead:

```bash
bash tools/docker_manus.sh down
bash tools/docker_manus.sh terminal
```

This opens a real interactive `/bin/bash` with the same USB passthrough, host
network and MANUS configuration volume. The container automatically sources
`/opt/ros/${ROS_DISTRO}/setup.bash` and `/work/ros2_ws/install/setup.bash` for
the entrypoint and for interactive Bash shells. From that terminal you can run
the publisher yourself:

```bash
ros2 run manus_ros2 manus_data_publisher --ros-args -p connection_attempts:=5
```

In another host terminal, launch RViz2 after sourcing the host workspace:

```bash
source /opt/ros/jazzy/setup.bash
source ros2_ws/install/setup.bash
ros2 launch manus_ros2 manus_rviz.launch.py
```

Use `Ctrl+C` to stop a foreground ROS command, then `exit` to remove the
interactive container. Do not run `terminal` while `up` is active: both would
start separate Core Integrated clients and compete for the same dongle/license.

After changing the Dockerfile, rebuild the image before starting a new
container so the automatic setup hook is included:

```bash
bash tools/docker_manus.sh build
```

You can also use the terminal mode to inspect data without starting the
publisher command automatically:

```bash
bash tools/docker_manus.sh terminal
ros2 topic list
ros2 topic echo /manus_glove_0
ros2 topic hz /manus_glove_0
```

The `shell` command remains available for attaching to a publisher that was
started with `up`:

```bash
bash tools/docker_manus.sh shell
```

You can run that command from any other host terminal. It opens another
interactive `/bin/bash` in the already running `manus` service; it does not
start a second MANUS Core client:

```bash
cd ~/Desktop/Hand_retargetting
newgrp docker                 # only if this shell lacks Docker permission
bash tools/docker_manus.sh shell
```

Run `shell` only when the container was started with `up`. If the container was
started with `terminal`, keep using its original terminal as the controlling
shell; opening another `terminal` would create another one-off container and
could compete for the same dongle.

Useful commands:

```bash
bash tools/docker_manus.sh status
bash tools/docker_manus.sh check-usb
bash tools/docker_manus.sh verify
bash tools/docker_manus.sh terminal
bash tools/docker_manus.sh shell
bash tools/docker_manus.sh restart
bash tools/docker_manus.sh down
```

The SDK configuration is stored in the named `manus_config` volume through
`XDG_CONFIG_HOME=/var/lib/manus`, so container recreation does not discard the
Core settings.

## 인터랙티브 컨테이너에서 공식 WUJI 드라이버 실행

이미지에는 공식 `wujihandros2` 패키지와 `tools/wuji_sdk.env`에 고정된
`wujihandcpp` 버전,
robot-state-publisher, RViz 실행 의존성이 포함되어 있습니다. Compose 서비스는
USB 버스를 전달하지만 WUJI 드라이버를 자동으로 시작하지는 않습니다.

```bash
bash tools/docker_manus.sh build
bash tools/docker_manus.sh down
bash tools/docker_manus.sh terminal
```

포그라운드 터미널 안에서 먼저 연결된 손을 조회하십시오. 이 명령은 USB
시리얼 설명자만 읽으며 모터를 활성화하지 않습니다.

```bash
ros2 run wujihand_driver wujihand_list
```

출력된 시리얼 번호로 공식 드라이버를 실행하십시오.

```bash
ros2 launch wujihand_bringup wujihand.launch.py \
  hand_name:=hand_0 serial_number:=<WUJI_HAND_SERIAL>
```

호스트의 두 번째 터미널에서 실행 중인 같은 컨테이너에 접속하려면 다음을
사용하십시오.

```bash
bash tools/docker_manus.sh shell
```

upstream의 부드러운 home 스크립트를 실행한 뒤 모든 관절을 명시적으로
비활성화하십시오.

```bash
ros2 run wujihand_bringup home.py --ros-args \
  -p hand_name:=hand_0 -p duration:=1.5 -p rate:=120.0
ros2 service call /hand_0/set_enabled wujihand_msgs/srv/SetEnabled \
  "{finger_id: 255, joint_id: 255, enabled: false}"
```

이 방식이 공식 WUJI 실행 경로입니다. `wujihand_driver`가 손 연결을 독점해야
하므로 시작하기 전에 Wuji Studio나 다른 SDK 클라이언트를 종료하십시오.
마지막 명령은 의도적인 모터 제어 동작입니다.

## Verify both gloves

Inside the container, `verify` checks publisher counts and the stable hand
fields:

```bash
bash tools/docker_manus.sh verify
```

The expected messages have `side: Left`, `hand_id: 0` and `side: Right`,
`hand_id: 1`. Topic suffixes are discovery order, so consumers must use
`side`, `hand_id` and `glove_id` rather than assuming that `_0` is always one
particular hand.

## RViz2 on the host

Stop any native MANUS publisher before starting the container. Start the
container first, then launch the existing host RViz setup:

```bash
source /opt/ros/jazzy/setup.bash
source ros2_ws/install/setup.bash
ros2 launch manus_ros2 manus_rviz.launch.py
```

Run only one Docker publisher, one native publisher, and one marker bridge. Two
Core Integrated clients or two marker bridges can overwrite each other's data.

## Pairing and license troubleshooting

Stop the container before running the official interactive SDK client:

```bash
bash tools/docker_manus.sh down
cd vendor/manus/ManusSDK_v3.1.1/SDKClient_Linux
./SDKClient_Linux.out
```

Choose `1` for Core Integrated, then `P` in the main menu and `P` again in the
Glove Pairing menu. Exit the SDK client before running `bash tools/docker_manus.sh up`.

If logs repeatedly contain `No valid MANUS license`:

1. Confirm `lsusb -d 3325:0049` on the host.
2. Run `bash tools/docker_manus.sh check-usb`.
3. Reconnect the dongle and hand after installing the udev rules.
4. Ensure no native publisher, SDK client or second container is using Core.
5. Confirm the dongle has the SDK component license.

The image build defaults to ROS 2 Jazzy to match the native workspace. Set
`ROS_DISTRO` explicitly if another ROS 2 distribution is required:

```bash
ROS_DISTRO=jazzy bash tools/docker_manus.sh build
```

## Docker에서 MANUS → WUJI retargeting 실행

이미지 빌드 시 공식 `wuji-retargeting` 코드와 NLOPT/Pinocchio 의존성을 함께
설치합니다. 컨테이너를 `terminal` 또는 `shell`로 연 뒤 같은 ROS 명령을
실행하십시오.

```bash
# 터미널 1: 컨테이너 내부
ros2 launch wujihand_bringup wujihand.launch.py \
  hand_name:=hand_0 serial_number:=<WUJI_HAND_SERIAL> rviz:=false

# 터미널 2: 같은 컨테이너에 다시 접속
bash tools/docker_manus.sh shell
ros2 run manus_wuji_retargeting manus_wuji_retargeting --ros-args \
  -p side:=right -p hand_name:=hand_0
```

MANUS publisher는 `up`으로 실행 중인 서비스에서 이미 동작하므로, retargeting
노드는 그 publisher가 발행하는 `/manus_glove_0`와 `/manus_glove_1`을
구독합니다. 왼손 WUJI를 별도 namespace로 실행할 때는 두 번째 노드에
`-p side:=left -p hand_name:=<LEFT_HAND_NAME>`을 지정합니다.
