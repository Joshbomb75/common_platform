# DEPLOY TO: ~/nine_scripts/nine_snap.py
#!/usr/bin/env python3
"""
Nine's camera capture script.
Expects camera node to already be running (managed by nine_camera.sh).
Subscribes to the camera topic, grabs one frame, saves to /tmp/nine_snap.jpg.
Prints: SNAP_OK:/tmp/nine_snap.jpg on success. Exits 1 on failure.
"""

import os
import sys
import time
import threading

# Ensure ROS2 Python packages are importable regardless of how this script is invoked
_ROS_PYPATH = "/opt/ros/kilted/lib/python3.12/site-packages"
if _ROS_PYPATH not in sys.path:
    sys.path.insert(0, _ROS_PYPATH)

# Unset super-client FastDDS profile — requires a discovery server that may not be running.
# Local multicast discovery works fine for single-machine ROS2.
os.environ.pop("FASTDDS_DEFAULT_PROFILES_FILE", None)

OUTPUT_PATH = "/tmp/nine_snap.jpg"
TOPIC_TIMEOUT = 20.0  # seconds to wait for first image
ROS_NAME = os.environ.get("ROS_NAME", "rcr002")
IMAGE_TOPIC = f"/{ROS_NAME}/camera/image_raw"


def main():
    import rclpy
    from rclpy.node import Node
    from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy, DurabilityPolicy
    from sensor_msgs.msg import Image

    rclpy.init()
    node = Node("nine_snap")
    received = threading.Event()
    image_data = {}

    def image_cb(msg: Image):
        if received.is_set():
            return
        image_data["msg"] = msg
        received.set()

    # Camera nodes publish BEST_EFFORT — must match or subscription silently receives nothing
    qos = QoSProfile(
        reliability=ReliabilityPolicy.BEST_EFFORT,
        history=HistoryPolicy.KEEP_LAST,
        depth=1,
        durability=DurabilityPolicy.VOLATILE,
    )
    sub = node.create_subscription(Image, IMAGE_TOPIC, image_cb, qos)

    deadline = time.time() + TOPIC_TIMEOUT
    while not received.is_set() and time.time() < deadline:
        rclpy.spin_once(node, timeout_sec=0.5)

    node.destroy_node()
    rclpy.shutdown()

    if not received.is_set():
        print("ERROR: Timed out waiting for camera image", file=sys.stderr)
        sys.exit(1)

    msg = image_data["msg"]
    saved = False

    # Try cv_bridge + cv2 first
    try:
        import cv2
        from cv_bridge import CvBridge
        bridge = CvBridge()
        cv_image = bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        cv2.imwrite(OUTPUT_PATH, cv_image)
        saved = True
    except ImportError:
        pass

    # Fallback: manual decode for rgb8 / bgr8
    if not saved:
        try:
            import numpy as np
            import cv2
            enc = msg.encoding.lower()
            arr = np.frombuffer(bytes(msg.data), dtype=np.uint8)
            arr = arr.reshape((msg.height, msg.width, 3))
            if enc in ("rgb8",):
                arr = arr[:, :, ::-1]  # RGB -> BGR for cv2
            cv2.imwrite(OUTPUT_PATH, arr)
            saved = True
        except Exception as e:
            print(f"ERROR: Image decode failed: {e}", file=sys.stderr)
            sys.exit(1)

    if saved:
        print(f"SNAP_OK:{OUTPUT_PATH}")
        sys.exit(0)
    else:
        print("ERROR: Could not save image", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

# Dependencies: rclpy, sensor_msgs (included with ROS2 kilted)
#               cv_bridge, python3-opencv (sudo apt install ros-kilted-cv-bridge python3-opencv)
#               numpy (usually pre-installed)
