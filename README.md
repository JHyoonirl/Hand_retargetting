# MANUS + WUJI 손 리타게팅

이 저장소는 ROS 2 패키지 소스를 `packages/`에 모으고, 독점 MANUS SDK와
하드웨어 설정을 분리합니다. 독립 실행에 필요한 빌드 결과는 `ros2_ws/`에 생성됩니다.
다른 저장소의 `ros2_ws/src/`에 submodule로 포함될 때는 `COLCON_IGNORE`로 기본 빌드에서
제외됩니다. `HAND_ROS_WS=/path/to/ros2_ws bash tools/build_ros.sh`를 사용하면 그
workspace의 `build/`와 `install/`에 Hand 패키지를 추가할 수 있습니다.

## RobotTeleoperationFramework 통합 Docker

프레임워크 루트의 Dockerfile은 이 저장소 설정을 참조해 Indy7, Vive, MANUS 입력,
MANUS-WUJI retargeting, WUJI 드라이버를 한 ROS 설치 경로에 넣을 수 있습니다.
Hand submodule을 초기화하고 MANUS SDK LFS 파일을 받은 뒤 프레임워크 루트에서 실행합니다.

```bash
git -C ros2_ws/src/hand_retargetting lfs pull
make docker-build INCLUDE_HAND=1
make docker-run INCLUDE_HAND=1
```

`INCLUDE_HAND=1`은 메인 Dockerfile의 `with-hand` 타깃을 선택합니다. WUJI SDK 버전과
체크섬은 `tools/wuji_sdk.env`를 사용하고, 패키지 의존성과 빌드 순서는 `tools/build_ros.sh`를
따릅니다. 이 타깃은 MANUS SDK를 이미지에 포함하므로 해당 이미지를
비공개로 관리하세요. 일반 `make docker-build`는 Hand SDK를 포함하지 않습니다.

통합 컨테이너 실행 시 USB 버스가 전달됩니다. MANUS publisher, retargeting 노드,
WUJI 드라이버는 자동으로 시작되지 않으며, 실행 순서와 하드웨어 권한 설정은 아래
Docker 및 하드웨어 안내를 따릅니다. 통합 컨테이너를 여러 터미널에서 쓸 때는 프레임워크
[README의 `docker exec` 예시](../../../README.md#hand-retargetting-프로젝트)를 사용합니다.
Hand 전용 이미지를 별도로 유지하려면 저장소 루트의 `make docker-build-hand`를 사용합니다.

```text
vendor/manus/ManusSDK_v3.1.1/  MANUS SDK, 라이브러리, 예제
packages/manus_ros2/          MANUS publisher와 RViz marker bridge
packages/manus_ros2_msgs/     MANUS 메시지 정의
packages/manus_wuji_retargeting/  MANUS-WUJI 리타게팅 노드
packages/wuji_hand/           공식 wujihandros2 Git checkout와 description 서브모듈
ros2_ws/                     독립 빌드 결과 (버전 관리 제외)
hardware/manus/                MANUS udev 규칙과 호스트 메모
hardware/wuji/                 WUJI 하드웨어 파일과 캘리브레이션 자료
downloads/wuji/                고정된 WUJI SDK 패키지 캐시(버전 관리 제외)
tools/                         빌드, 진단, 실행 스크립트
.venv/                         공용 Python/Open3D 가상환경
```

## 저장소 받기 (clone)

Ubuntu에서 Git과 Git LFS를 먼저 설치합니다. MANUS SDK의 대용량 `.so`
라이브러리는 Git LFS로 관리하므로, clone 전에 LFS를 활성화해야 합니다.

```bash
sudo apt update
sudo apt install git git-lfs
git lfs install

git clone --recurse-submodules https://github.com/JHyoonirl/Hand_retargetting.git
cd Hand_retargetting
git lfs pull
```

`--recurse-submodules`는 WUJI 드라이버와 그 안의 `wuji-description`까지
프로젝트에 기록된 커밋으로 내려받습니다. GitHub의 **Download ZIP** 대신 위
명령을 사용하세요. SDK 바이너리 다운로드에는 약 261MB가 추가로 필요합니다.

이미 일반 `git clone`으로 받은 경우에는 저장소 안에서 다음을 실행합니다.
Git LFS가 없다면 위 설치 명령부터 실행하세요.

```bash
git lfs install
git submodule update --init --recursive
git lfs pull
```

다운로드 결과를 확인할 수 있습니다.

```bash
git submodule status --recursive
git lfs fsck
```

서브모듈 상태의 커밋 앞에 `-`나 `+`가 없고, LFS 검사에서
`Git LFS fsck OK`가 표시되면 정상입니다.

이후 최신 프로젝트 변경 사항을 받을 때는 로컬 수정 사항을 먼저 커밋하거나
stash한 뒤, 최상위 폴더에서 실행합니다.

```bash
git pull --ff-only
git submodule sync --recursive
git submodule update --init --recursive
git lfs pull
```

clone은 소스와 SDK 파일을 받는 단계입니다. ROS 2, WUJI SDK, Python 가상환경과
빌드 결과는 별도로 준비해야 하며, 아래 설치·빌드 안내를 이어서 진행하세요.

## WUJI 손: 공식 드라이버

[`packages/wuji_hand`](packages/wuji_hand/README.integration.md)는 공식
[`wuji-technology/wujihandros2`](https://github.com/wuji-technology/wujihandros2)
저장소와 `wuji-description` 서브모듈을 포함한 checkout입니다. 별도의 WUJI
대체 드라이버나 임의로 만든 평활화 알고리즘은 사용하지 않습니다. 공식
드라이버가 `wujihandcpp`를 감싸고 `LowPass` 실시간 컨트롤러, 공식 home
스크립트, `set_enabled` 서비스를 제공합니다.

고정된 upstream checkout을 갱신하려면 다음을 실행하십시오.

```bash
bash tools/update_wuji_driver.sh
```

호스트에서 WUJI를 빌드하기 전에 프로젝트가 고정한 공식 SDK를 설치하십시오.
설치 파일은 `/tmp`가 아니라 작업공간의 `downloads/wuji/`에 캐시되며, 버전과
SHA-256 체크섬은 `tools/wuji_sdk.env`에서 관리합니다.

```bash
bash tools/install_wuji_sdk.sh
```

이 명령은 시스템 라이브러리 경로에 SDK를 설치하므로 최초 실행 시 sudo
비밀번호가 필요합니다. Docker를 사용하는 경우에는 `docker_manus.sh build`가
동일한 고정 버전을 이미지 안에 자동으로 설치하므로 호스트에 SDK를 설치할
필요가 없습니다.

Docker 이미지는 `docker_manus.sh build` 중 같은 패키지를 설치합니다. 다음과
같이 작업공간을 빌드하십시오.

```bash
source /opt/ros/jazzy/setup.bash
bash tools/build_ros.sh -DBUILD_TESTING=OFF
source ros2_ws/install/setup.bash
```

WUJI 손을 연결한 뒤 공식 드라이버를 실행하십시오.

```bash
ros2 launch wujihand_bringup wujihand.launch.py hand_name:=hand_0
```

공식 토픽을 확인한 뒤, 지원되는 home 동작을 수행하고 모터를 비활성화할 수
있습니다.

```bash
ros2 topic echo /hand_0/joint_states --once
ros2 run wujihand_bringup home.py --ros-args \
  -p hand_name:=hand_0 -p duration:=1.5 -p rate:=120.0
ros2 service call /hand_0/set_enabled wujihand_msgs/srv/SetEnabled \
  "{finger_id: 255, joint_id: 255, enabled: false}"
```

서비스 호출은 의도적으로 모터를 비활성화합니다. 드라이버, 손 방향, 관절
상태 스트림을 확인하기 전에는 실행하지 마십시오. 공식 저장소가 안내하는
배포판은 Kilted/Humble이고 이 프로젝트는 Jazzy를 사용하므로, 대상 장비에서
빌드 결과를 확인해야 합니다. Docker 이미지는 USB 버스를 노출하지만 MANUS와
함께 WUJI 드라이버를 자동 실행하지는 않습니다.

The required MANUS 3.1.1 headers and Linux libraries are already stored under
`vendor/manus/ManusSDK_v3.1.1/`; the project does not require the separate
Downloads SDK directory for normal builds or calibration.

Build the ROS workspace with:

```bash
source /opt/ros/jazzy/setup.bash
bash tools/build_ros.sh -DBUILD_TESTING=OFF
source ros2_ws/install/setup.bash
```

Start MANUS and RViz2 separately:

```bash
ros2 run manus_ros2 manus_data_publisher --ros-args -p connection_attempts:=5
ros2 launch manus_ros2 manus_rviz.launch.py
```

RViz launch도 한 번만 실행해야 합니다. 여러 marker bridge가 동시에 실행되면 같은 `ns/id` marker를 서로 덮어써 한 손이 느리거나 튀어 보일 수 있습니다. 기존 RViz를 닫을 때는 해당 launch 터미널에서 `Ctrl+C`를 누른 뒤 다시 실행하세요.

marker bridge는 양손의 최신 메시지를 모아 하나의 `MarkerArray`로 약 120 Hz에 발행하고, 출력 큐는 최신 메시지 1개만 유지합니다. 따라서 한 손의 오래된 marker가 RViz 큐에 쌓여 다른 손보다 늦게 보이지 않습니다.

Core Integrated는 한 번에 한 프로세스만 실행해야 합니다. 시작 직후에는 동글에서 라이선스 정보가 도착하기 전까지 `No valid MANUS license`가 한 번 출력될 수 있습니다. 몇 초 뒤 동글 라이선스와 장갑이 연결되고 `/manus_glove_0`가 발행되면 정상 상태입니다. 같은 오류가 계속 반복되면 기존 publisher 또는 MANUS Core를 먼저 종료한 뒤 publisher를 한 번만 다시 실행하세요.

## 두 장갑 무선 페어링

장갑 LED가 다르게 보이면 다음 순서로 확인합니다.

- 파란색 고정: 이미 동글/Core에 연결된 장갑으로 보입니다.
- 흰색 깜빡임: 동글에 아직 등록되지 않아 페어링을 기다리는 상태로 보입니다.

Core Integrated를 두 개 실행하면 서로 충돌하므로, 페어링할 때는 ROS publisher를 먼저 중지합니다. 실행 중인 터미널에서 `Ctrl+C`를 누르거나 다음 명령을 사용합니다.

```bash
pkill -INT -f '/ros2_ws/install/manus_ros2/lib/manus_ros2/manus_data_publisher'
```

그 다음 MANUS 공식 Linux SDK client에서 페어링합니다.

```bash
cd vendor/manus/ManusSDK_v3.1.1/SDKClient_Linux
./SDKClient_Linux.out
```

화면의 입력 순서는 다음과 같습니다.

1. SDK 모드 선택에서 `1`을 눌러 `Core Integrated`를 선택합니다.
2. Main Menu에서 `P` (`Go To Pairing Menu`)를 누릅니다.
3. `Glove Pairing` 메뉴에서 `P` (`Pair first available Glove`)를 누릅니다.
4. 페어링 성공 메시지를 확인한 뒤 `Q`로 이전 메뉴로 돌아가고 `Esc`로 SDK client를 종료합니다.

오른손 장갑이 흰색으로 깜빡이는 동안 이 절차를 실행해야 합니다. `No glove available for pairing found`가 나오면 장갑의 페어링 모드를 다시 켜고, 같은 동글에 연결되어 있는지 확인한 뒤 2–3단계를 반복합니다. SDK client와 ROS publisher를 동시에 실행하지 마세요.

페어링이 끝나면 publisher를 하나만 다시 시작하고 양손을 확인합니다.

```bash
source /opt/ros/jazzy/setup.bash
source ros2_ws/install/setup.bash
ros2 run manus_ros2 manus_data_publisher --ros-args -p connection_attempts:=5
```

토픽 번호는 발견 순서라서 손을 식별할 때 번호만 사용하지 말고 메시지의 `side`와 `hand_id`를 확인합니다. 오른손은 `side: Right`, `hand_id: 1`, 왼손은 `side: Left`, `hand_id: 0`이어야 합니다.

```bash
source /opt/ros/jazzy/setup.bash
source ros2_ws/install/setup.bash
ros2 topic hz /manus_glove_0
```

RViz의 marker bridge는 양손을 서로 마주 보는 형태로 표시하기 위해 `mirror_left=true`와 `mirror_right=true`를 사용합니다. 이 좌우 반전은 시각화에만 적용되고 `/manus_glove_0` 원본 메시지나 WUJI retargeting 입력은 변경하지 않습니다.

기본 RViz 화면에서 왼손은 화면 왼쪽, 오른손은 화면 오른쪽에 오도록 표시 오프셋을 적용합니다(현재 월드 좌표는 왼손 `x=+0.12 m`, 오른손 `x=-0.12 m`). 이 오프셋은 시각화 전용이며 원본 장갑 좌표와 WUJI retargeting 입력에는 적용되지 않습니다. 간격을 바꾸려면 launch 파일의 `hand_separation`을 조정하고, 원래 위치에 겹쳐 표시하려면 `separate_hands`를 `False`로 설정합니다. 각 marker에는 색이 다른 `Left (hand_id 0)` 또는 `Right (hand_id 1)` 라벨이 표시됩니다.

각 `ManusGlove` 메시지는 `side` 문자열과 안정적인 `hand_id`를 함께 제공합니다. `hand_id`는 왼손 `0`, 오른손 `1`, 알 수 없음 `-1`이며, `glove_id`는 실제 MANUS 장갑 하드웨어 ID입니다.

The project-level integration notes are in [README.integration.md](README.integration.md).

The Docker deployment guide is in [README.docker.md](README.docker.md). It
covers host udev setup, USB passthrough, the Docker wrapper script and
container-side ROS verification.

Glove calibration is available through the official Linux SDK client:

```bash
bash tools/manus_calibrate.sh
```

See [hardware/manus/README.md](hardware/manus/README.md#calibrate-a-glove) for
the key sequence and the required Core Integrated/publisher shutdown order.

## MANUS → WUJI Hand retargeting

공식 [`wuji-hand-teleop`](https://github.com/wuji-technology/wuji-hand-teleop)의
MANUS 경로를 이 workspace에 맞게 넣었습니다. `manus_wuji_retargeting` 노드는
`/manus_glove_0`와 `/manus_glove_1`을 모두 구독하고 `msg.side`가 일치하는
프레임만 선택합니다. 선택한 MANUS raw node를 upstream이 정한 21점 입력 순서로
변환한 뒤, vendorized된 공식 [`wuji-retargeting`](https://github.com/wuji-technology/wuji-retargeting)의
`Retargeter`로 20개 WUJI 관절각을 계산하여 `/{hand_name}/joint_commands`에
발행합니다. 여기서 21점 배열은 retargeter의 내부 입력 형식일 뿐이며 카메라
MediaPipe를 실행하지 않습니다.

처음 한 번만 retargeting 런타임을 설치합니다. `.venv`를 활성화한 상태에서
실행하면 모든 Python 의존성이 프로젝트 가상환경에 들어갑니다.

```bash
source .venv/bin/activate
bash tools/install_wuji_retargeting.sh
```

그 다음 workspace를 다시 빌드합니다.

```bash
source /opt/ros/jazzy/setup.bash
bash tools/build_ros.sh -DBUILD_TESTING=OFF
source ros2_ws/install/setup.bash
```

현재 연결된 오른손 WUJI가 `hand_0`이라면 터미널을 다음 순서로 엽니다.

> **중요:** WUJI 드라이버가 이미 실행 중이면 터미널 1을 다시 실행하지 마십시오.
> `/hand_0/joint_states`가 이미 나오는데 `wujihand.launch.py`를 한 번 더 실행하면
> USB 인터페이스가 중복 점유되어 `Failed to claim interface: -6 (ERROR_BUSY)`가
> 발생합니다. 이 경우 MANUS publisher와 터미널 3의 retargeting만 실행합니다.

```bash
# 터미널 1: WUJI 공식 드라이버 (처음 시작할 때만, 한 번만 실행)
ros2 launch wujihand_bringup wujihand.launch.py \
  hand_name:=hand_0 serial_number:=385336653533 rviz:=false

# 터미널 2: MANUS Core Integrated publisher
ros2 run manus_ros2 manus_data_publisher --ros-args -p connection_attempts:=5

# 터미널 3: 오른손 MANUS → hand_0 retargeting
ros2 launch manus_wuji_retargeting manus_wuji_retargeting.launch.py \
  side:=right hand_name:=hand_0
```

현재 프로세스가 이미 떠 있는지 먼저 확인하려면 다음을 사용합니다.

```bash
ros2 topic hz /hand_0/joint_states
ros2 topic hz /manus_glove_0
```

두 명령 모두 데이터가 나오면 새 WUJI launch를 실행하지 않고 터미널 3만
실행하십시오. 상세한 재시작 순서와 dry-run 절차는
[retargeting README](packages/manus_wuji_retargeting/README.md)를 참고하십시오.

명령 노드가 시작되면 `/hand_0/set_enabled`를 한 번 호출해 전체 관절을 자동으로
enable합니다. 따라서 이전 테스트에서 모터를 disable한 상태에서도 새 세션을
시작할 수 있습니다. retargeting을 중지해도 모터를 자동 disable하지는 않습니다.
안전하게 종료하려면 별도 터미널에서 다음을 실행하십시오.

```bash
ros2 service call /hand_0/set_enabled wujihand_msgs/srv/SetEnabled \
  "{finger_id: 255, joint_id: 255, enabled: false}"
```

실제 명령이 손으로 가지 않는 계산 검증은 다음처럼 할 수 있습니다.

```bash
ros2 launch manus_wuji_retargeting manus_wuji_retargeting.launch.py \
  side:=right hand_name:=hand_0 dry_run:=true enable_on_start:=false
```

WUJI 드라이버 없이 계산 결과를 RViz에서 보려면 다음을 사용합니다. 이 명령은
`/hand_0/joint_states`에 dry-run 관절값을 발행하고 WUJI URDF와 RViz를 함께
실행합니다.

```bash
ros2 launch manus_wuji_retargeting manus_wuji_retargeting.launch.py \
  side:=right hand_name:=hand_0 \
  dry_run:=true visualize_dry_run:=true rviz:=true \
  enable_on_start:=false
```

이 모드에서는 같은 `hand_name`의 WUJI 드라이버를 동시에 실행하지 마십시오.

정상 동작 확인 명령은 다음과 같습니다. MANUS 라이선스가 유효하고 장갑 프레임이
들어와야 `joint_commands`가 발행됩니다.

```bash
ros2 topic hz /manus_glove_0
ros2 topic hz /hand_0/joint_commands
ros2 topic echo /hand_0/joint_commands --once
```

왼손도 같은 방식으로 별도 프로세스를 실행하되 `side:=left`와 왼손 WUJI
driver의 namespace를 지정합니다. 공식 설정은 오른손 `z=-15°`, 왼손 `z=+15°`를
사용하며, 양손을 동시에 구동할 때도 장갑 번호가 아니라 `msg.side`로 라우팅합니다.
