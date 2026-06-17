"""
motion 노드 요약

1. 입력
   - LaneInfo(/cam0/lane_info): 차선 번호, 조향 각도, 차량 위치 오프셋
   - String(traffic_light_result): 신호등 검출 결과 문자열

2. 처리 흐름
   - 원래는 차선 번호와 신호등 상태를 함께 보고
     차선 유지 / 차선 변경 / 속도 조절을 결정했다.
   - steering, left_speed, right_speed를 계산해 MotionCommand를 발행했다.

3. 출력
   - MotionCommand(motion_command): steering, left_speed, right_speed

현재는 핵심 판단 로직을 제거하고, 입력/출력 구조만 남긴 skeleton 이다.
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from interfaces_pkg.msg import LaneInfo, MotionCommand

class MotionNode(Node):
    def __init__(self):
        super().__init__('motion')

        # Inputs:
        # - LaneInfo: 차선 추종에 필요한 조향/차선 번호/위치 정보
        # - String: 신호등 검출 결과 문자열
        self.create_subscription(LaneInfo, '/cam0/lane_info', self.lane_info_callback, 10)
        self.create_subscription(String, 'traffic_light_result', self.traffic_callback, 10)

        # Output:
        # - MotionCommand: 최종 주행 명령(steering, left_speed, right_speed)
        self.motion_pub = self.create_publisher(MotionCommand, 'motion_command', 10)

        # Core decision state was removed; keep only the input/output skeleton.
        self.last_lane_info = None
        self.last_traffic_msg = None

    def traffic_callback(self, msg):
        # Input handler for traffic_light_result.
        # The original implementation parsed Detected/Area values here and
        # used them to trigger lane-change state transitions.
        self.last_traffic_msg = msg.data

    def lane_info_callback(self, msg):
        # Input handler for LaneInfo.
        # Original behavior: decide steering and speed from lane_num, steering_angle,
        # and vehicle_position_x, then publish MotionCommand.
        self.last_lane_info = msg

        cmd = MotionCommand()
        cmd.steering = 0
        cmd.left_speed = 0
        cmd.right_speed = 0
        self.motion_pub.publish(cmd)

        # The detailed lane-following and lane-change logic was removed.
        # This node now preserves the message flow only.

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
