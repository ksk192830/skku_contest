"""
Obstacle 감지 파이프라인 요약

1. 입력
    - 카메라 이미지(Image): 원본 프레임
    - 세그멘테이션/검출 결과(DetectionArray): 한 프레임의 검출 목록
    - message_filters로 두 입력을 같은 시점 기준으로 동기화

2. 처리 흐름
    - 원래는 car class 후보를 골라 중심 영역 안의 장애물만 선택
    - bbox 크기, 중심 위치, 면적, 높이 값을 계산
    - 계산 결과를 상태 문자열과 시각화 이미지로 출력

3. 출력
    - obstacle_result(String): Detected / Area / Height 형태의 상태 문자열
    - /cam0/obstacle_mask(Image): 장애물 시각화용 이미지

입력과 출력의 관계는 아래처럼 읽으면 된다.
- 입력: Image + DetectionArray
- 출력: obstacle_result(String) + /cam0/obstacle_mask(Image)
- 현재 상태: 핵심 계산은 제거되어 있고, 출력은 인터페이스 유지용 placeholder

현재는 핵심 선택/계산 로직을 비워두고,
입력-출력 구조와 파이프라인 흐름만 남겨둔 상태다.
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy, QoSDurabilityPolicy

import numpy as np
from std_msgs.msg import String
from sensor_msgs.msg import Image
from interfaces_pkg.msg import DetectionArray

from cv_bridge import CvBridge
from message_filters import Subscriber, ApproximateTimeSynchronizer


class ObstacleNode(Node):
    def __init__(self):
        super().__init__('obstacle')

        self.bridge = CvBridge()

        qos = QoSProfile(
            reliability=QoSReliabilityPolicy.RELIABLE,
            history=QoSHistoryPolicy.KEEP_LAST,
            durability=QoSDurabilityPolicy.VOLATILE,
            depth=1
        )

        self.image_sub = Subscriber(self, Image, '/cam0/image_raw', qos_profile=qos)
        self.detection_sub = Subscriber(self, DetectionArray, '/cam0/detections', qos_profile=qos)

        self.ts = ApproximateTimeSynchronizer(
            [self.image_sub, self.detection_sub],
            queue_size=10,
            slop=0.5
        )
        self.ts.registerCallback(self.sync_callback)

        self.result_pub = self.create_publisher(String, 'obstacle_result', qos)
        self.mask_pub = self.create_publisher(Image, '/cam0/obstacle_mask', qos)

    def sync_callback(self, img_msg, det_msg):
        # Input path:
        # - img_msg: Image, 원본 카메라 프레임
        # - det_msg: DetectionArray, 같은 시점의 검출 목록
        # - 원래는 det_msg 안의 car 후보를 검사해서 obstacle를 고르는 자리였다
        cv_img = self.bridge.imgmsg_to_cv2(img_msg, desired_encoding='bgr8')

        # Output path:
        # - status_msg: 장애물 감지 결과를 문자열로 내보내는 출력
        # - mask_msg: 장애물 시각화 이미지를 내보내는 출력
        # - 지금은 핵심 로직이 없어서 입력에 의해 계산하지 않고 placeholder만 유지
        status = False
        final_area = 0
        height_val = 0

        status_msg = String(
            data=f"Detected: {status}, Area: {final_area}, Height: {height_val}"
        )
        self.result_pub.publish(status_msg)

        # Mask/visualization output:
        # 원래는 선택된 car bbox를 화면에 오버레이했지만,
        # 지금은 출력 인터페이스만 유지하기 위해 빈 캔버스를 publish 한다.
        mask_img = np.zeros_like(cv_img)
        mask_msg = self.bridge.cv2_to_imgmsg(mask_img, encoding='bgr8')
        self.mask_pub.publish(mask_msg)


def main(args=None):
    rclpy.init(args=args)
    node = ObstacleNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
