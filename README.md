# SKKU Autonomous Driving Contest Workspace

성균관대 자율주행 경진대회 실습용 ROS 2 워크스페이스입니다.

이 저장소는 카메라, LiDAR, 판단, 제어, 시뮬레이션 패키지를 포함합니다. 일부 핵심 알고리즘은 학습과 구현을 위해 skeleton 또는 TODO 형태로 남겨둘 수 있습니다.

## 1. 기본 개념

ROS 2에서는 프로그램 하나하나를 **노드(node)** 라고 부릅니다.

예를 들어 카메라 이미지를 publish하는 프로그램도 노드이고, YOLO 추론을 하는 프로그램도 노드입니다. 여러 노드를 한 번에 실행하는 파일이 **launch 파일**입니다.

자주 쓰는 명령은 아래 4개입니다.

```bash
ros2 run <패키지이름> <실행파일이름>
ros2 launch <패키지이름> <런치파일이름>
ros2 topic list
ros2 topic echo <토픽이름>
```

## 2. 처음 받았을 때 실행 순서

### 2.1 자동 초기 세팅

처음 clone 받은 뒤에는 `install.sh`를 한 번 실행합니다.

이 스크립트가 해주는 일:

```text
필요한 apt 패키지 설치
Python 패키지 설치
Gazebo 모델 복사
~/.bashrc에 편의 alias 추가
colcon build --symlink-install 실행
기본 환경 검증
```

실행:

```bash
cd ~/skku_contest
source /opt/ros/humble/setup.bash
bash install.sh --auto
```

GPU가 없는 노트북이면 CPU 모드로 실행해도 됩니다.

```bash
bash install.sh --cpu
```

설치 없이 현재 환경만 확인하고 싶으면:

```bash
bash install.sh --verify-only
```

### 2.2 새 터미널에서 매번 해야 하는 것

터미널을 새로 열면 ROS 2와 이 워크스페이스를 다시 활성화해야 합니다.

```bash
cd ~/skku_contest
source /opt/ros/humble/setup.bash
source install/setup.bash
```

`install.sh`를 실행했다면 `~/.bashrc`에 alias가 추가됩니다. 새 터미널에서는 아래처럼 짧게 실행할 수도 있습니다.

```bash
humble
skku_ws
skku_source
```

### 2.3 빌드가 잘 됐는지 확인

```bash
ros2 pkg list | grep camera_pkg
ros2 pkg list | grep launch_pkg
```

패키지 이름이 출력되면 ROS 2가 이 워크스페이스를 인식한 것입니다.

## 3. 패키지 구조

```text
src/
  camera_pkg/           카메라 입력, YOLO segmentation, 차선/신호등/횡단보도/장애물 인식
  lidar_pkg/            LiDAR scan publish, 시각화, clustering
  decision_making_pkg/  주행 판단, 미션 판단
  control_pkg/          차량 제어, 키보드 제어
  simulation_pkg/       Gazebo 시뮬레이션 보조 노드
  interfaces_pkg/       커스텀 msg 정의
  launch_pkg/           여러 노드를 한 번에 실행하는 launch 파일과 RViz 설정
```

## 4. 주요 노드 설명과 실행법

노드를 단독 실행하기 전에 항상 아래를 먼저 실행하세요.

```bash
cd ~/skku_contest
source install/setup.bash
```

### 4.1 camera_pkg

| 실행 파일 | 설명 | 기본 실행 |
| --- | --- | --- |
| `image` | 카메라, 이미지 폴더, 비디오 파일을 읽어서 `sensor_msgs/Image`로 publish합니다. | `ros2 run camera_pkg image` |
| `yolo_seg` | YOLO segmentation 모델로 객체/마스크를 검출합니다. | `ros2 run camera_pkg yolo_seg` |
| `lane` | 카메라 이미지와 detection 결과를 받아 차선 정보를 publish합니다. | `ros2 run camera_pkg lane` |
| `traffic_light` | 이미지와 detection 결과를 받아 신호등 상태를 판단합니다. | `ros2 run camera_pkg traffic_light` |
| `obstacle` | detection 결과를 기반으로 장애물 상태를 판단합니다. | `ros2 run camera_pkg obstacle` |
| `cross_walk_detect` | detection 결과를 기반으로 횡단보도 정보를 판단합니다. | `ros2 run camera_pkg cross_walk_detect` |
| `image_saver` | 이미지 토픽을 파일로 저장합니다. 데이터 수집할 때 사용합니다. | `ros2 run camera_pkg image_saver` |

카메라 번호를 바꾸고 싶으면 parameter를 넘깁니다.

```bash
ros2 run camera_pkg image --ros-args -p data_source:=camera -p cam_num:=0 -p pub_topic:=/cam0/image_raw
```

이미지 저장 경로를 바꾸고 싶으면 아래처럼 실행합니다.

```bash
ros2 run camera_pkg image_saver --ros-args \
  -p sub_topic:=/cam0/image_raw \
  -p save_dir:=$HOME/skku_contest_images/test
```

### 4.2 lidar_pkg

| 실행 파일 | 설명 | 기본 실행 |
| --- | --- | --- |
| `scan` | RPLiDAR 데이터를 읽어서 `/scan_raw` 토픽으로 publish합니다. | `ros2 run lidar_pkg scan` |
| `scan_viz` | LiDAR scan을 OpenCV 창으로 시각화합니다. | `ros2 run lidar_pkg scan_viz` |
| `scan_cluster` | LiDAR scan을 clustering하고 주차 공간 정보를 publish합니다. | `ros2 run lidar_pkg scan_cluster` |

LiDAR 포트를 바꿔야 하면 아래처럼 실행합니다.

```bash
ros2 run lidar_pkg scan --ros-args -p lidar_port:=/dev/ttyUSB0 -p pub_topic:=/scan_raw
```

포트 확인은 아래 명령으로 합니다.

```bash
ls /dev/ttyUSB*
```

### 4.3 decision_making_pkg

| 실행 파일 | 설명 | 기본 실행 |
| --- | --- | --- |
| `motion` | 일반 주행 판단 노드입니다. 차선 정보 등을 받아 `MotionCommand`를 publish합니다. | `ros2 run decision_making_pkg motion` |
| `motion_mission` | 미션 주행 판단 노드입니다. 차선, 신호등, 횡단보도, LiDAR 정보를 함께 사용합니다. | `ros2 run decision_making_pkg motion_mission` |

이 패키지는 경진대회에서 가장 많이 수정하게 될 가능성이 큽니다.

### 4.4 control_pkg

| 실행 파일 | 설명 | 기본 실행 |
| --- | --- | --- |
| `control` | `MotionCommand`를 받아 실제 차량 제어 명령으로 변환합니다. | `ros2 run control_pkg control` |
| `control_p` | 주차 또는 별도 제어용 노드입니다. | `ros2 run control_pkg control_p` |
| `keyboard_controller` | 키보드 입력으로 차량을 수동 조작합니다. | `ros2 run control_pkg keyboard_controller` |

아두이노나 모터 컨트롤러 포트가 다르면 코드 또는 parameter에서 포트를 확인해야 합니다.

### 4.5 simulation_pkg

| 실행 파일 | 설명 | 기본 실행 |
| --- | --- | --- |
| `load_ego_car_node` | Gazebo에 ego 차량 모델을 spawn합니다. | `ros2 run simulation_pkg load_ego_car_node` |
| `load_ego_car_parking_node` | 주차 환경용 ego 차량을 spawn합니다. | `ros2 run simulation_pkg load_ego_car_parking_node` |
| `load_obstable_car_node` | 장애물 차량을 spawn합니다. | `ros2 run simulation_pkg load_obstable_car_node` |
| `load_traffic_light_node` | 신호등 모델을 spawn합니다. | `ros2 run simulation_pkg load_traffic_light_node` |
| `sim_simulation_sender_node` | `MotionCommand`를 Gazebo 제어 토픽으로 변환합니다. | `ros2 run simulation_pkg sim_simulation_sender_node` |
| `timer_based_obstacle_mover` | 시간 기반으로 장애물을 움직입니다. | `ros2 run simulation_pkg timer_based_obstacle_mover` |
| `simulation_keyboard_controller` | 시뮬레이션 차량을 키보드로 조작합니다. | `ros2 run simulation_pkg simulation_keyboard_controller` |
| `traffic_light_keyboard_controller` | 시뮬레이션 신호등 상태를 키보드로 바꿉니다. | `ros2 run simulation_pkg traffic_light_keyboard_controller` |
| `direct_cmdvel_model_driver` | `/cmd_vel` 기반으로 Gazebo 모델을 직접 움직입니다. | `ros2 run simulation_pkg direct_cmdvel_model_driver` |
| `motion_command_entity_driver` | `MotionCommand`로 Gazebo entity를 움직입니다. | `ros2 run simulation_pkg motion_command_entity_driver` |
| `motion_command_ros2control_bridge` | `MotionCommand`를 ros2_control 명령으로 변환합니다. | `ros2 run simulation_pkg motion_command_ros2control_bridge` |

## 5. Launch 파일 설명과 실행법

Launch 파일은 여러 노드를 한 번에 실행합니다.

실행 전:

```bash
cd ~/skku_contest
source install/setup.bash
```

### 5.1 general.py

일반 차선 주행용 launch입니다.

실행되는 주요 노드:

```text
camera_pkg/image
camera_pkg/yolo_seg
camera_pkg/lane
decision_making_pkg/motion
rviz2
```

실행:

```bash
ros2 launch launch_pkg general.py
```

카메라 번호가 맞지 않으면 `src/launch_pkg/launch/general.py`에서 `cam_num` 값을 수정하세요.

### 5.2 mission.py

미션 주행용 launch입니다. 일반 차선 주행보다 많은 인식 노드가 켜집니다.

실행되는 주요 노드:

```text
camera_pkg/image
camera_pkg/yolo_seg
camera_pkg/lane
camera_pkg/traffic_light
camera_pkg/obstacle
camera_pkg/cross_walk_detect
lidar_pkg/scan
decision_making_pkg/motion_mission
rviz2
```

실행:

```bash
ros2 launch launch_pkg mission.py
```

LiDAR 포트가 다르면 `src/launch_pkg/launch/mission.py`에서 `/dev/ttyUSB0` 값을 수정하세요.

### 5.3 data_collection.py

카메라 이미지를 저장하기 위한 launch입니다.

기본 저장 위치:

```text
~/skku_contest_images/parking_front_new
~/skku_contest_images/parking_rear_new
```

실행:

```bash
ros2 launch launch_pkg data_collection.py
```

저장 위치를 바꿔 실행할 수도 있습니다.

```bash
ros2 launch launch_pkg data_collection.py \
  cam0_save_dir:=$HOME/skku_contest_images/front_test \
  cam1_save_dir:=$HOME/skku_contest_images/rear_test
```

## 6. RViz2 사용법

RViz2는 ROS 토픽을 눈으로 확인하는 도구입니다.

### 6.1 launch와 함께 실행

`general.py`, `mission.py`는 RViz2를 자동으로 실행합니다.

```bash
ros2 launch launch_pkg general.py
```

또는:

```bash
ros2 launch launch_pkg mission.py
```

### 6.2 RViz2만 따로 실행

```bash
rviz2
```

설정 파일을 지정해서 실행하려면:

```bash
rviz2 -d install/launch_pkg/share/launch_pkg/rviz/general.rviz
```

또는 source 폴더의 설정을 직접 열 수도 있습니다.

```bash
rviz2 -d src/launch_pkg/rviz/general.rviz
```

### 6.3 RViz2에서 자주 보는 항목

왼쪽 아래 `Add` 버튼을 눌러 display를 추가합니다.

자주 쓰는 display:

```text
Image       카메라 이미지 확인
LaserScan   LiDAR scan 확인
Marker      시각화 marker 확인
TF          좌표계 확인
```

예시 토픽:

```text
/cam0/image_raw
/cam0/seg_vis
/scan_raw
/motion_command
```

화면에 아무것도 안 보이면 먼저 토픽이 살아있는지 확인하세요.

```bash
ros2 topic list
ros2 topic hz /cam0/image_raw
ros2 topic echo /motion_command
```

## 7. 토픽 확인 기본 명령

현재 실행 중인 토픽 목록:

```bash
ros2 topic list
```

토픽 타입 확인:

```bash
ros2 topic info /cam0/image_raw
```

토픽 내용 출력:

```bash
ros2 topic echo /motion_command
```

토픽 publish 주기 확인:

```bash
ros2 topic hz /cam0/image_raw
```

노드 목록:

```bash
ros2 node list
```

노드 상세 정보:

```bash
ros2 node info /motion_node
```

## 8. 자주 나는 문제

### 8.1 `Package not found`

워크스페이스 setup을 source하지 않은 경우가 많습니다.

```bash
cd ~/skku_contest
source install/setup.bash
```

### 8.2 `ros2: command not found`

ROS 2 자체가 활성화되지 않았습니다.

```bash
source /opt/ros/humble/setup.bash
```

### 8.3 카메라가 안 열림

카메라 번호를 확인하세요.

```bash
ls /dev/video*
```

launch 파일의 `cam_num` 값을 바꾸거나, 단독 실행할 때 parameter를 넘깁니다.

```bash
ros2 run camera_pkg image --ros-args -p cam_num:=0
```

### 8.4 LiDAR가 안 열림

포트 이름과 권한을 확인하세요.

```bash
ls /dev/ttyUSB*
sudo chmod 666 /dev/ttyUSB0
```

그 다음 다시 실행합니다.

```bash
ros2 run lidar_pkg scan --ros-args -p lidar_port:=/dev/ttyUSB0
```

### 8.5 YOLO가 GPU를 못 씀

이 코드는 GPU가 없으면 자동으로 CPU를 사용하도록 되어 있습니다.

강제로 CPU를 쓰려면:

```bash
SKKU_YOLO_DEVICE=cpu ros2 launch launch_pkg general.py
```

GPU를 쓰려면:

```bash
SKKU_YOLO_DEVICE=cuda:0 ros2 launch launch_pkg general.py
```

### 8.6 코드를 수정했는데 반영이 안 됨

Python 파일만 수정했고 `--symlink-install`로 빌드했다면 보통 다시 빌드하지 않아도 됩니다. 그래도 이상하면 다시 빌드하세요.

```bash
cd ~/skku_contest
colcon build --symlink-install
source install/setup.bash
```

## 9. 추천 실습 순서

처음에는 한 번에 launch부터 실행하지 말고 작은 단위로 확인하는 것을 추천합니다.

1. `ros2 run camera_pkg image`로 카메라 토픽 확인
2. `ros2 topic list`로 `/image_raw` 또는 `/cam0/image_raw` 확인
3. `ros2 run camera_pkg yolo_seg`로 detection 토픽 확인
4. `ros2 run camera_pkg lane`로 차선 정보 확인
5. `ros2 run decision_making_pkg motion`로 제어 명령 확인
6. `ros2 launch launch_pkg general.py`로 전체 실행
7. `ros2 launch launch_pkg mission.py`로 미션 실행

한 단계씩 확인하면 어디서 문제가 생기는지 훨씬 빨리 찾을 수 있습니다.
