# WUJI 로봇 손

공식 WUJI ROS 2 드라이버는 독점 `wujihandcpp` SDK에 의존하므로 별도의
upstream 저장소로 유지합니다. 손 시리얼 번호, 펌웨어 메모, 캘리브레이션
파일, 현장별 udev 규칙은 이 디렉터리에 보관하십시오.

현재 WUJI USB 장치는 `0483:2000`으로 식별됩니다. 호스트에서 MANUS와 WUJI
규칙을 함께 설치하려면 다음을 실행한 뒤 손을 다시 연결하십시오.

```bash
sudo bash tools/install_udev_rules.sh
```

`ros2_ws/src/wuji_hand`의 공식 드라이버가 사용하는 토픽과 서비스는 다음과
같습니다.

```text
/<hand_name>/joint_states     sensor_msgs/msg/JointState
/<hand_name>/joint_commands   공식 WUJI 드라이버 입력
/<hand_name>/set_enabled      공식 WUJI 드라이버의 모터 활성화 서비스
```

`set_enabled(false)`는 모든 관절의 모터를 비활성화하지만, WUJI Hand 1의
기계적 self-locking 구조를 사람이 직접 역구동할 수 있게 만드는 relax 모드는
아닙니다. 현재 공식 ROS 2 드라이버에는 임피던스나 backdrive 인터페이스가
없으므로 `ControlMode`나 `effort_limit`을 임의로 조작하지 마십시오.

MANUS ROS 2 publisher는 `manus_ros2_msgs/msg/ManusGlove` 형식으로
`/manus_glove_0`과 `/manus_glove_1`을 제공합니다. 이후 retargeter는 손
방향이 일치하는 MANUS 토픽을 구독하고, 공식 드라이버가 지원하는 20관절
`sensor_msgs/JointState`를 `/<hand_name>/joint_commands`로 직접 발행할 수
있습니다. 명령 평활화는 별도 추정 알고리즘 대신 공식 드라이버에 내장된
`LowPass` 실시간 컨트롤러를 사용하십시오.
