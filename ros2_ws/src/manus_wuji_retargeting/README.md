# MANUS → WUJI ROS 2 리타게팅

이 패키지는 공식 [`wuji-hand-teleop`](https://github.com/wuji-technology/wuji-hand-teleop)의
MANUS 입력 경로와 공식 [`wuji-retargeting`](https://github.com/wuji-technology/wuji-retargeting)을
현재 ROS 2 workspace의 WUJI 드라이버에 연결합니다.

```text
MANUS Core Integrated
        │
        ▼
/manus_glove_0, /manus_glove_1   (ManusGlove)
        │
        ▼
manus_wuji_retargeting         (side로 좌/우 선택)
        │
        ▼
/hand_0/joint_commands           (20개 관절각)
        │
        ▼
wujihand_driver                 (실제 USB WUJI Hand)
```

이 노드는 카메라나 MediaPipe를 실행하지 않습니다. MANUS의 25개 raw node를
upstream이 정한 21점 입력 순서로 바꾼 뒤, 공식 `Retargeter`로 WUJI의 20개
관절 명령을 계산합니다. `side` 값으로 장갑을 선택하므로 `/manus_glove_0`와
`/manus_glove_1`의 번호가 바뀌어도 좌우가 뒤섞이지 않습니다.

현재 MANUS SDK 3.1.1 프레임은 숫자 ID가 `0..24`이고, 실제 의미는 메시지의
`chain_type`/`joint_type`에 들어 있습니다. 구현은 숫자 ID를 하드코딩하지 않고
이 metadata로 다음 순서를 만듭니다.

```text
wrist(Hand/Invalid)
thumb: MCP, PIP, DIP, TIP
index/middle/ring/pinky: PIP, IP, DIP, TIP
```

MANUS의 일반 손가락에는 MediaPipe의 네 손가락 점보다 앞에 metacarpal 점이 하나
더 있습니다. 공식 WUJI MANUS adapter와 같이 그 첫 `MCP`를 제외하고 MANUS의
`PIP/IP/DIP/TIP`을 MediaPipe의 `MCP/PIP/DIP/TIP` 자리에 대응시킵니다. 이 방식은
SDK가 0-based 또는 예전 1-based node ID를 사용해도 chain/joint metadata가
유지되는 한 같은 결과를 냅니다.

리타게팅 설정은 공식 optimizer의 hyperextension 및 PIP/DIP coupling 항도
활성화합니다. 손을 폈을 때 한 관절은 음의 하한까지 꺾이고 다음 관절은 크게
굽혀지는 동일 끝점의 S자 해를 억제하기 위한 설정입니다.

## 먼저 알아둘 점: `ERROR_BUSY (-6)`

WUJI 드라이버는 USB 인터페이스를 독점합니다. 이미 다음과 같은 launch가 실행 중인
상태에서 `wujihand.launch.py`를 다시 실행하면 두 번째 프로세스가 USB를 차지하려고
하여 다음 오류가 납니다.

```text
Failed to claim interface: -6 (ERROR_BUSY)
Failed to connect to WujiHand hardware
```

이 오류는 동글이나 손이 고장났다는 뜻이 아니라 **같은 WUJI 드라이버를 두 번
실행했다는 뜻**입니다. `/hand_0/joint_states`가 이미 나오면 기존 드라이버를
그대로 사용하고, 새 터미널에서는 MANUS publisher와 이 retargeting 노드만
실행하십시오. 드라이버를 재시작하려면 기존 launch를 실행한 터미널에서 먼저
`Ctrl+C`로 종료한 뒤 한 번만 다시 시작합니다.

현재 프로세스와 토픽은 다음으로 확인할 수 있습니다.

```bash
ps -ef | rg 'wujihand_driver|manus_data_publisher'
ros2 topic list | rg 'manus_glove|hand_0'
ros2 topic hz /hand_0/joint_states
```

## 최초 설치와 빌드

프로젝트 루트(`/home/jhyoon/Desktop/Hand_retargetting`)에서 한 번 실행합니다.

```bash
source /opt/ros/jazzy/setup.bash
source .venv/bin/activate
bash tools/install_wuji_retargeting.sh
bash tools/build_ros.sh -DBUILD_TESTING=OFF
source ros2_ws/install/setup.bash
```

`install_wuji_retargeting.sh`는 `vendor/wuji-retargeting`에 보관한 공식 코드와
Numpy, SciPy, NLOPT, Pinocchio, PyYAML 의존성을 `.venv`에 설치합니다. 소스가
바뀌면 `build_ros.sh`만 다시 실행하면 됩니다.

## 하드웨어 없이 dry-run 결과를 RViz에서 보기

WUJI 드라이버를 실행하지 않은 상태에서 MANUS publisher만 실행하고 다음 명령을
사용하면 됩니다. 이 모드는 실제 `joint_commands`를 발행하지 않고,
`/hand_0/joint_states`에 계산된 20개 관절각을 발행합니다. 같은 launch가 WUJI
URDF의 `robot_state_publisher`와 RViz도 시작합니다.

```bash
ros2 launch manus_wuji_retargeting manus_wuji_retargeting.launch.py \
  side:=right hand_name:=hand_0 \
  dry_run:=true visualize_dry_run:=true rviz:=true \
  enable_on_start:=false
```

RViz가 열리면 Fixed Frame은 오른손에서 `right_palm_link`, 왼손에서
`left_palm_link`를 사용합니다. 관절값이 계속 갱신되는지 확인하려면 다음을
사용합니다.

```bash
ros2 topic hz /hand_0/joint_states
ros2 topic echo /hand_0/joint_states --once
```

이 모드에서는 같은 `hand_name`으로 WUJI 하드웨어 드라이버를 동시에 실행하지
마십시오. 실제 드라이버가 이미 실행 중이면 `visualize_dry_run`을 켜지 말고,
하드웨어 드라이버가 사용하는 `/hand_0/joint_states`와 충돌하지 않는 별도
namespace를 사용해야 합니다.

## 지금처럼 드라이버가 이미 실행 중일 때

현재 `/hand_0/joint_states`가 나오고 MANUS publisher도 실행 중이면 아래 명령만
실행하면 됩니다. WUJI launch를 다시 실행하지 마십시오.

```bash
cd /home/jhyoon/Desktop/Hand_retargetting
source /opt/ros/jazzy/setup.bash
source .venv/bin/activate
source ros2_ws/install/setup.bash

# 장갑 방향과 입력이 맞는지 확인
ros2 topic echo /manus_glove_0 --once | rg 'side:|hand_id:'
ros2 topic hz /manus_glove_0

# 먼저 계산만 확인: 모터 명령을 발행하지 않음
ros2 launch manus_wuji_retargeting manus_wuji_retargeting.launch.py \
  side:=right hand_name:=hand_0 dry_run:=true enable_on_start:=false
```

계산 결과가 정상이고 실제 구동할 준비가 되었으면 `Ctrl+C`로 dry-run을 종료한
뒤 다음을 실행합니다.

```bash
ros2 launch manus_wuji_retargeting manus_wuji_retargeting.launch.py \
  side:=right hand_name:=hand_0
```

기본값 `enable_on_start:=true`이면 노드가 `/hand_0/set_enabled`에 전체 관절
enable 요청을 한 번 보냅니다. retargeting 노드를 종료해도 모터를 자동으로
disable하지는 않습니다.

정상적으로 명령이 발행되는지 다른 터미널에서 확인합니다.

```bash
ros2 topic hz /hand_0/joint_commands
ros2 topic echo /hand_0/joint_commands --once
```

`/manus_glove_0`의 `side`가 `Right`, `hand_id`가 `1`이면 `side:=right`를
사용합니다. `Left`, `hand_id`가 `0`이면 `side:=left`를 사용합니다.

## 처음부터 세 프로세스를 시작할 때

각 명령은 별도 터미널에서 실행합니다. WUJI 드라이버는 한 번만 실행해야 합니다.

터미널 1 — WUJI 드라이버:

```bash
source /opt/ros/jazzy/setup.bash
source ros2_ws/install/setup.bash
ros2 launch wujihand_bringup wujihand.launch.py \
  hand_name:=hand_0 serial_number:=385336653533 rviz:=false
```

터미널 2 — MANUS Core Integrated publisher:

```bash
source /opt/ros/jazzy/setup.bash
source ros2_ws/install/setup.bash
ros2 run manus_ros2 manus_data_publisher --ros-args -p connection_attempts:=5
```

터미널 3 — MANUS 오른손을 WUJI `hand_0`으로 전송:

```bash
source /opt/ros/jazzy/setup.bash
source .venv/bin/activate
source ros2_ws/install/setup.bash
ros2 launch manus_wuji_retargeting manus_wuji_retargeting.launch.py \
  side:=right hand_name:=hand_0
```

왼손 WUJI를 별도 드라이버 namespace로 실행할 때는 두 번째 retargeting 노드를
다음처럼 실행합니다. `hand_name`은 실제 왼손 드라이버 namespace와 같아야 합니다.

```bash
ros2 launch manus_wuji_retargeting manus_wuji_retargeting.launch.py \
  side:=left hand_name:=hand_1
```

양손을 동시에 구동할 때는 WUJI 드라이버 두 개가 각각 서로 다른 USB 장치와
namespace를 가져야 합니다. 장갑 번호만 보고 좌우를 지정하지 말고 항상 `side`를
확인하십시오.

## 종료와 모터 disable

다음 순서로 종료하면 재실행 때 USB 점유와 잔류 명령을 줄일 수 있습니다.

1. retargeting 터미널에서 `Ctrl+C`
2. MANUS publisher 터미널에서 `Ctrl+C`
3. WUJI launch 터미널에서 `Ctrl+C`

모터를 명시적으로 disable하려면 WUJI 드라이버가 살아 있는 동안 실행합니다.

```bash
ros2 service call /hand_0/set_enabled wujihand_msgs/srv/SetEnabled \
  "{finger_id: 255, joint_id: 255, enabled: false}"
```

## 문제 해결

| 증상 | 확인할 내용 |
|---|---|
| `ERROR_BUSY (-6)` | WUJI launch가 이미 실행 중인지 확인하고 두 번째 드라이버를 종료 |
| `No right MANUS frame` | MANUS license, publisher, `side` 값, `/manus_glove_0/1` 토픽 확인 |
| `joint_commands`가 0 Hz | `dry_run`이 true인지 확인하고, 20개 finite 관절값이 생성되는지 확인 |
| `No valid MANUS license` | SDK component license가 연결된 MANUS dongle/Core인지 확인 |
| `joint_states`가 없음 | `home.launch.py`는 드라이버를 시작하지 않음. 실제 홈 동작은 WUJI launch를 먼저 실행하고, 하드웨어 없는 확인은 `visualize_dry_run:=true` 사용 |

공식 참고 문서는 다음과 같습니다.

- [wuji-hand-teleop](https://github.com/wuji-technology/wuji-hand-teleop)
- [공식 MANUS 입력 문서](https://github.com/wuji-technology/wuji-hand-teleop/blob/main/src/input_devices/manus_input/README.md)
- [wuji-retargeting](https://github.com/wuji-technology/wuji-retargeting)
