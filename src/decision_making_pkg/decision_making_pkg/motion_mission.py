#!/usr/bin/env python3
"""
motion_mission 노드 요약

1. 입력
   - LaneInfo(/cam0/lane_info): 차선 번호, 조향 각도, 차량 위치 오프셋
   - String(traffic_light_result): 신호등 상태 문자열
   - String(obstacle_result): 장애물 상태 문자열
   - CrossWalk(cross_walk_result): 횡단보도 상태 메시지
   - LaserScan(/scan_raw): LiDAR 거리 데이터

2. 처리 흐름
   - 원래는 차선 변경, 신호등 정지/출발, 장애물 회피, LiDAR 기반 차선 전환을 함께 판단했다.
   - 각 callback에서 상태를 갱신한 뒤, lane_info_callback에서 MotionCommand를 계산했다.

3. 출력
   - MotionCommand(motion_command): steering, left_speed, right_speed

현재는 핵심 결정 로직을 제거하고, 입력-상태-출력 구조만 남긴 skeleton 이다.
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from interfaces_pkg.msg import LaneInfo, MotionCommand, CrossWalk
from sensor_msgs.msg import LaserScan


class MotionNode(Node):
    def __init__(self):
        super().__init__('motion_mission')

        # Inputs:
        # - LaneInfo, String, CrossWalk, LaserScan을 각각 별도 callback으로 받는다.
        self.create_subscription(LaneInfo, '/cam0/lane_info', self.lane_info_callback, 10)
        self.create_subscription(String, 'traffic_light_result', self.traffic_callback, 10)
        self.create_subscription(String, 'obstacle_result', self.obstacle_callback, 10)
        self.create_subscription(CrossWalk, 'cross_walk_result', self.cross_walk_callback, 10)
        self.create_subscription(LaserScan, '/scan_raw', self.lidar_callback, 10)

        # Output:
        # - MotionCommand: 최종 주행 명령
        self.motion_pub = self.create_publisher(MotionCommand, 'motion_command', 10)

        # State placeholders preserved for readability.
        self.current_lane = None
        self.target_lane = 2
        self.is_changing_lane = False
        self.stop_state = False

        self.traffic_light_detected = False
        self.traffic_light_area = 0.0
        self.traffic_light_color = ''

        self.cross_walk_found = False
        self.cross_walk_height = None

        self.obstacle_detected = False
        self.obstacle_height = 0.0

        self.latest_lidar_avg = None

        self.last_lane_info = None
        self.last_motion_command = None

    def lidar_callback(self, msg: LaserScan):
        # Input handler for LaserScan.
        # The original implementation averaged a target sector to decide lane changes.
        self.latest_lidar_avg = None
        _ = msg


    def obstacle_callback(self, msg: String):
        # Input handler for obstacle_result.
        # The original implementation parsed Detected/Area/Height and used it for lane decision.
        self.obstacle_detected = False
        self.obstacle_height = 0.0
        _ = msg

    def cross_walk_callback(self, msg: CrossWalk):
        # Input handler for cross_walk_result.
        self.cross_walk_found = msg.found
        self.cross_walk_height = msg.height

    def traffic_callback(self, msg):
        # Input handler for traffic_light_result.
        self.traffic_light_detected = False
        self.traffic_light_area = 0.0
        self.traffic_light_color = ''
        _ = msg

    def lane_info_callback(self, msg: LaneInfo):
        # Main decision input for lane-following.
        # Originally this callback combined lane keeping, lane changes,
        # traffic light stop/resume, obstacle avoidance, and LiDAR checks.
        self.current_lane = msg.lane_num
        self.last_lane_info = msg

        cmd = MotionCommand()
        cmd.steering = 0
        cmd.left_speed = 0
        cmd.right_speed = 0
        self.last_motion_command = cmd
        self.motion_pub.publish(cmd)

        _ = msg
    
def main(args=None):
    rclpy.init(args=args)
    node = MotionNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('MotionNode interrupted')
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
