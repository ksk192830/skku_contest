#!/usr/bin/env python3
"""
횡단보도 감지 파이프라인 요약

1. 입력
    - 카메라 이미지(Image): 원본 프레임
    - 횡단보도 검출 결과(DetectionArray): 한 프레임의 검출 목록
    - message_filters로 두 입력을 동기화해서 처리

2. 처리 흐름
    - 원래는 class_name == crosswalk 인 후보를 찾음
    - bbox를 이미지 경계 안으로 자르고, 높이(top_y)와 박스 목록을 계산
    - 결과를 메시지와 마스크 이미지로 출력

3. 출력
    - cross_walk_result(CrossWalk): found, height 형태의 상태 메시지
    - /cam0/cross_walk_mask(Image): 시각화 또는 마스크용 이미지

입력과 출력의 관계는 아래처럼 읽으면 된다.
- 입력: Image + DetectionArray
- 출력: CrossWalk + /cam0/cross_walk_mask(Image)
- 현재 상태: 핵심 선택/계산 로직은 제거했고, 인터페이스 유지용 skeleton만 남김
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy, QoSDurabilityPolicy

import cv2
from cv_bridge import CvBridge
from message_filters import Subscriber, ApproximateTimeSynchronizer
from sensor_msgs.msg import Image

from interfaces_pkg.msg import DetectionArray, CrossWalk


class CrossWalkNode(Node):
    def __init__(self):
        super().__init__("cross_walk_node")

        self.bridge = CvBridge()

        qos = QoSProfile(
            reliability=QoSReliabilityPolicy.RELIABLE,
            history=QoSHistoryPolicy.KEEP_LAST,
            durability=QoSDurabilityPolicy.VOLATILE,
            depth=1,
        )

        image_topic = "/cam0/image_raw"
        detection_topic = "/cam0/detections_cw"
        mask_topic = "/cam0/cross_walk_mask"
        result_topic = "cross_walk_result"

        self.image_sub = Subscriber(self, Image, image_topic, qos_profile=qos)
        self.detection_sub = Subscriber(self, DetectionArray, detection_topic, qos_profile=qos)
        self.ts = ApproximateTimeSynchronizer(
            [self.image_sub, self.detection_sub],
            queue_size=10,
            slop=0.5,
        )
        self.ts.registerCallback(self.sync_callback)

        # Outputs:
        # - CrossWalk: found / height 정보를 내보내는 상태 메시지
        # - Image: 횡단보도 시각화용 마스크 이미지
        self.result_pub = self.create_publisher(CrossWalk, result_topic, qos)
        self.mask_pub = self.create_publisher(Image, mask_topic, qos)

    def sync_callback(self, img_msg: Image, det_msg: DetectionArray):
        # Input path:
        # - img_msg: Image, 원본 카메라 프레임
        # - det_msg: DetectionArray, 같은 시점의 횡단보도 검출 목록
        cv_img = self.bridge.imgmsg_to_cv2(img_msg, desired_encoding="bgr8")

        # Output path:
        # 핵심 bbox 선택과 height 계산 로직은 제거되어 placeholder만 유지한다.
        found, height, boxes = self.extract_cross_walk(det_msg, cv_img.shape[1], cv_img.shape[0])

        result = CrossWalk()
        result.found = found
        result.height = int(height)
        self.result_pub.publish(result)

        # Visualization output:
        # 원래는 crosswalk bbox를 덮어쓴 이미지를 publish했지만,
        # 지금은 인터페이스 유지용 빈 캔버스를 내보낸다.
        out_img = cv_img.copy()
        mask_msg = self.bridge.cv2_to_imgmsg(out_img, encoding="bgr8")
        self.mask_pub.publish(mask_msg)

    def extract_cross_walk(self, detections: DetectionArray, img_w: int, img_h: int):
        # 핵심 로직 제거 전의 입력/출력 형태를 남겨둔 placeholder 함수.
        # 원래는 crosswalk 후보 박스들을 골라 found / height / boxes를 계산했다.
        _ = detections
        _ = img_w
        _ = img_h
        found = False
        top_y_min = 0
        boxes = []
        return found, top_y_min, boxes



def main(args=None):
    rclpy.init(args=args)
    node = CrossWalkNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
