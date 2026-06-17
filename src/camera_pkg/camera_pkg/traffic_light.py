"""
신호등 감지 파이프라인 요약

1. 입력
    - 카메라 이미지(Image): 원본 프레임
    - 신호등 검출 결과(DetectionArray): 한 프레임의 검출 목록
    - message_filters로 두 입력을 동기화해서 처리

2. 처리 흐름
    - 원래는 traffic_light 후보를 찾아 ROI를 자름
    - ROI에서 HSV 색 마스크를 만들고 red / yellow / green 면적을 비교
    - 최대 면적 색상을 신호등 상태로 선택
    - 결과를 문자열 상태와 마스크 이미지로 출력

3. 출력
    - traffic_light_result(String): Detected / Area / Color 형태의 상태 문자열
    - /cam0/traffic_light_mask(Image): 시각화 또는 마스크용 이미지

입력과 출력의 관계는 아래처럼 읽으면 된다.
- 입력: Image + DetectionArray
- 출력: String + /cam0/traffic_light_mask(Image)
- 현재 상태: 핵심 색 판정 로직은 제거했고, 인터페이스 유지용 skeleton만 남김
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy, QoSDurabilityPolicy

from std_msgs.msg import String
from sensor_msgs.msg import Image
from interfaces_pkg.msg import DetectionArray

from cv_bridge import CvBridge
from message_filters import Subscriber, ApproximateTimeSynchronizer


class TrafficLightNode(Node):
    def __init__(self):
        super().__init__('traffic_light_node')

        self.bridge = CvBridge()
        self.last_status = None
        self.declare_parameter('image_topic', '/cam0/image_raw')
        self.declare_parameter('detection_topic', '/cam0/detections')
        self.declare_parameter('result_topic', 'traffic_light_result')
        self.declare_parameter('mask_topic', '/cam0/traffic_light_mask')

        image_topic = self.get_parameter('image_topic').value
        detection_topic = self.get_parameter('detection_topic').value
        result_topic = self.get_parameter('result_topic').value
        mask_topic = self.get_parameter('mask_topic').value

        qos = QoSProfile(
            reliability=QoSReliabilityPolicy.RELIABLE,
            history=QoSHistoryPolicy.KEEP_LAST,
            durability=QoSDurabilityPolicy.VOLATILE,
            depth=1
        )

        # 원본 영상 & DetectionArray 동기화 (기존 퍼블리셔 유지)
        self.image_sub     = Subscriber(self, Image,          image_topic,     qos_profile=qos)
        self.detection_sub = Subscriber(self, DetectionArray, detection_topic, qos_profile=qos)
        self.ts            = ApproximateTimeSynchronizer(
            [self.image_sub, self.detection_sub],
            queue_size=10,
            slop=0.5
        )
        self.ts.registerCallback(self.sync_callback)

        # 결과 문자열 퍼블리셔
        self.pub      = self.create_publisher(String, result_topic, qos)
        # → 마스킹 영상 퍼블리셔 추가
        self.mask_pub = self.create_publisher(Image,  mask_topic, qos)

    def sync_callback(self, img_msg, det_msg):
        # Input path:
        # - img_msg: Image, 원본 카메라 프레임
        # - det_msg: DetectionArray, 같은 시점의 신호등 검출 목록
        cv_img = self.bridge.imgmsg_to_cv2(img_msg, desired_encoding='bgr8')

        # Output path:
        # - 상태 문자열은 유지하지만, 현재는 핵심 판정 로직을 제거해서 placeholder 값을 보낸다
        # - 마스크 이미지는 인터페이스 유지용으로만 publish 한다
        detected, area, color = self.detect_traffic_light_color(cv_img, det_msg)
        status_msg = f"Detected: {detected}, Area: {area}, Color: {color}"
        out = String()
        out.data = status_msg
        self.pub.publish(out)
        self.last_status = status_msg

        # Visualization output:
        # 원래는 traffic_light bbox와 색상에 따라 overlay를 만들었지만,
        # 지금은 빈/원본 프레임만 유지해서 마스크 퍼블리셔 인터페이스를 살린다.
        mask_msg = self.bridge.cv2_to_imgmsg(cv_img, encoding='bgr8')
        self.mask_pub.publish(mask_msg)

    def detect_traffic_light_color(self, image, detections: DetectionArray):
        # 핵심 색 판정 로직을 제거한 placeholder 함수.
        # 원래는 traffic_light 후보의 ROI를 잘라 HSV 마스크로 red/yellow/green 면적을 비교했다.
        _ = image
        _ = detections
        return False, 0, 'none'


def main(args=None):
    rclpy.init(args=args)
    node = TrafficLightNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
