from setuptools import find_packages, setup
import os
from glob import glob


def collect_files_with_dirs(base_dir):
    collected = []
    for root, _, files in os.walk(base_dir):
        file_paths = [os.path.join(root, f) for f in files if os.path.isfile(os.path.join(root, f))]
        if file_paths:
            rel_dir = os.path.relpath(root, 'camera_pkg')
            collected.append((os.path.join('share', package_name, rel_dir), file_paths))
    return collected


package_name = 'camera_pkg'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        # launch 파일 설치 경로 추가
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
        # 모델 파일(.pt) 설치
        (os.path.join('share', package_name, 'model'), glob('camera_pkg/model/*')),
    ] + collect_files_with_dirs('camera_pkg/lib'),
    install_requires=['setuptools', 'rosidl_runtime_py'],  # 'rosidl_runtime_py' 추가
    zip_safe=True,
    maintainer='sg',
    maintainer_email='sg@todo.todo',
    description='TODO: Package description',
    license='TODO: License declaration',
    tests_require=['pytest'],
    dependency_links=[
        'https://github.com/ros2/rosidl_runtime_py',  # ROS 2 Python 런타임 의존성 링크
    ],
    entry_points={
        'console_scripts': [
             'image = camera_pkg.image_publisher:main',
             'yolo_seg = camera_pkg.yolo_seg:main',
             'traffic_light = camera_pkg.traffic_light:main',
             'lane = camera_pkg.lane_detect:main',
             'obstacle = camera_pkg.obstacle:main',
             'image_saver = camera_pkg.image_saver:main',
             'cross_walk_detect = camera_pkg.cross_walk_detect:main',
             
        ],
    },
)

