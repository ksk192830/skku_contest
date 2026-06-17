"""
차선 감지 파이프라인 요약

1. 입력
    - 카메라 이미지(Image): 원본 카메라 프레임
    - 세그멘테이션 기반 차선 검출 결과(DetectionArray): 한 프레임의 검출 목록
      * det.class_name == lane1 / lane2 를 사용해 차선 마스크를 만든다
      * det.mask.data 안의 점들을 이미지 좌표로 해석한다

2. 처리 흐름
    - 검출 결과를 이미지 좌표의 마스크로 변환
    - BEV(원근 변환) 단계 적용: 기준점은 나중에 직접 튜닝
    - 후처리, 경계 복원, 차선 중심 추정, 조향 계산 순서로 진행

3. 출력
    - 차선 상태 메시지(LaneInfo): steering_angle, lane_num, vehicle_position_x
    - 시각화용 이미지(lane_viz): 중간 처리 상태를 눈으로 확인하는 용도

이 파일은 현재 핵심 계산 로직을 비워둔 상태이며,
후배가 전체 파이프라인의 읽는 순서를 이해할 수 있도록
단계 구조와 주석만 남겨둔 버전이다.
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import (
    QoSProfile,
    QoSReliabilityPolicy,
    QoSHistoryPolicy,
    QoSDurabilityPolicy,
)
from sensor_msgs.msg import Image
from interfaces_pkg.msg import DetectionArray, LaneInfo
from cv_bridge import CvBridge
import cv2
import numpy as np


class LaneDetector(Node):
    def __init__(self):
        super().__init__("lane_detector")

        # Parameters
        self.declare_parameter("camera_topic", "image_raw")
        self.declare_parameter("detection_topic", "detections")

        cam_topic = self.get_parameter("camera_topic").value
        det_topic = self.get_parameter("detection_topic").value

        qos = QoSProfile(
            reliability=QoSReliabilityPolicy.RELIABLE,
            history=QoSHistoryPolicy.KEEP_LAST,
            durability=QoSDurabilityPolicy.VOLATILE,
            depth=5,
        )

        self.bridge = CvBridge()

        # Cache latest detections
        self.last_det_msg = None
        self.last_det_time_ns = 0

        # Inputs: camera image and lane detections arrive separately.
        # The node keeps the latest detection message and combines it with the next image callback.
        self.det_sub = self.create_subscription(
            DetectionArray, det_topic, self.det_callback, qos
        )
        self.img_sub = self.create_subscription(
            Image, cam_topic, self.image_callback, qos
        )

        # Outputs:
        # - LaneInfo: steering_angle, lane_num, vehicle_position_x
        # - lane_viz: 처리 흐름을 확인하는 시각화 이미지
        self.viz_pub = self.create_publisher(Image, "lane_viz", qos)
        self.lane_info_pub = self.create_publisher(LaneInfo, "lane_info", qos)

        # Last selected lane (1 or 2)
        self.last_lane = None

        # Safety: if detections are too old, we still publish fallback
        self.DETECTION_MAX_AGE_SEC = 0.8

        self.get_logger().info(f"LaneDetector initialized: {cam_topic}, {det_topic}")

    def det_callback(self, det_msg: DetectionArray):
        self.last_det_msg = det_msg
        self.last_det_time_ns = self.get_clock().now().nanoseconds

    def publish_fallback(self):
        # LaneInfo fields:
        # - steering_angle: 차선 기반 조향 각도
        # - lane_num: 현재 참조한 차선 번호
        # - vehicle_position_x: 차선 중심 대비 차량의 x 오프셋
        lane_num = self.last_lane if self.last_lane is not None else 1
        msg = LaneInfo()
        msg.steering_angle = 0
        msg.lane_num = lane_num
        msg.vehicle_position_x = 0
        self.lane_info_pub.publish(msg)
        self.last_lane = lane_num

    def image_callback(self, img_msg: Image):
        # Input path:
        # 1) keep the most recent detections in det_callback()
        # 2) combine them with the current image here
        if self.last_det_msg is None:
            self.publish_fallback()
            return

        # If detections too old, publish fallback
        now_ns = self.get_clock().now().nanoseconds
        age_sec = (now_ns - self.last_det_time_ns) / 1e9
        if age_sec > self.DETECTION_MAX_AGE_SEC:
            self.publish_fallback()
            return

        self.process(img_msg, self.last_det_msg)

    def process(self, img_msg: Image, det_msg: DetectionArray):
        try:
            frame = self.bridge.imgmsg_to_cv2(img_msg, "bgr8")
            h, w = frame.shape[:2]

            # Input 1: detection polygons in image coordinates.
            # Original behavior: rasterize lane1/lane2 masks from segmentation results.
            # DetectionArray는 한 프레임의 검출 묶음이고, 각 Detection의 mask를 차선 후보로 사용한다.
            mask1 = np.zeros((h, w), np.uint8)
            mask2 = np.zeros((h, w), np.uint8)
            for det in det_msg.detections:
                if det.class_name not in ("lane1", "lane2"):
                    continue
                pts = np.array([[int(p.x), int(p.y)] for p in det.mask.data], np.int32)
                if pts.shape[0] < 3:
                    continue
                pts[:, 0] = np.clip(pts[:, 0], 0, w - 1)
                pts[:, 1] = np.clip(pts[:, 1], 0, h - 1)
                if det.class_name == "lane1":
                    cv2.fillPoly(mask1, [pts], 255)
                else:
                    cv2.fillPoly(mask2, [pts], 255)

            # Input 2 -> internal stage: perspective transform to BEV-style coordinates.
            # This keeps the intended pipeline visible even though the detailed math is removed.
            # BEV 기준점은 외부에서 직접 튜닝할 수 있도록 코드 내부 상수는 두지 않는다.
            # 현재는 변환 단계의 위치만 남겨둔 상태다.
            M = np.eye(3, dtype=np.float32)
            bw1 = cv2.warpPerspective(mask1, M, (w, h), flags=cv2.INTER_LINEAR)
            bw2 = cv2.warpPerspective(mask2, M, (w, h), flags=cv2.INTER_LINEAR)

            # Internal stage: post-processing / cleanup placeholder.
            # The detailed morphology, boundary extraction, and lane fitting logic were removed.
            proc1 = bw1
            proc2 = bw2
            valid = np.ones((h, w), dtype=bool)

            # Internal stage: lane geometry recovery placeholder.
            # Previously this block recovered boundaries, estimated centerlines, and derived steering.
            #    Keep this placeholder so the intended reading order remains obvious to future readers.
            bev = np.zeros((h, w, 3), np.uint8)
            bev[:] = (0, 50, 0)
            bev[(proc1 > 0) | (proc2 > 0)] = (0, 0, 0)
            bev[~valid] = (50, 50, 50)
            cv2.putText(
                bev,
                "Lane pipeline skeleton: mask -> BEV -> postprocess -> centerline -> publish",
                (20, max(30, h // 12)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2,
                cv2.LINE_AA,
            )

            # Output path:
            # publish a safe fallback LaneInfo and a visualization frame so the interfaces stay alive.
            self.publish_fallback()
            self.viz_pub.publish(self.bridge.cv2_to_imgmsg(bev, "bgr8"))

        except Exception as e:
            self.get_logger().error(f"LaneDetector exception: {type(e).__name__}: {e}")
            self.publish_fallback()


def main(args=None):
    rclpy.init(args=args)
    node = LaneDetector()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Interrupted")
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()