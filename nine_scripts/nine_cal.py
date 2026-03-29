# DEPLOY TO: ~/nine_scripts/nine_cal.py
#!/usr/bin/env python3
"""
Nine's wheel calibration script.

Usage:
  python3 nine_cal.py straight <distance_m>   — drive straight, report odom
  python3 nine_cal.py spin <degrees>          — spin in place, report odom
  python3 nine_cal.py correct <actual_m> <commanded_m>   — compute wheel_radius correction
  python3 nine_cal.py correct_spin <actual_deg> <commanded_deg>  — compute wheel_sep correction

For straight calibration:
  1. Mark start position on floor
  2. Run: python3 nine_cal.py straight 1.0
  3. Measure actual distance traveled with tape measure
  4. Run: python3 nine_cal.py correct <actual_m> 1.0
  5. Update wheel_radius in ~/ros2_ws/src/common_platform/config/my_controllers.yaml

For spin calibration (do after wheel_radius is dialed in):
  1. Mark robot heading with tape
  2. Run: python3 nine_cal.py spin 360
  3. Measure actual rotation angle
  4. Run: python3 nine_cal.py correct_spin <actual_deg> 360
  5. Update wheel_separation in the same YAML

Current values (from my_controllers.yaml):
  wheel_radius:    0.033 m
  wheel_separation: 0.297 m

Velocity pipeline: /cmd_vel → twist_mux → /rcr002/cmd_vel → Teensy
Runs at constant velocity (no ramp) for clean distance math.
"""

import sys
import math
import time
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry

# ─── Config ────────────────────────────────────────────────────────────────────
CAL_LINEAR_SPEED  = 0.20   # m/s — slow and safe for calibration
CAL_ANGULAR_SPEED = 0.60   # rad/s — slow spin
PUBLISH_HZ        = 20.0
CMD_VEL_TOPIC     = "/cmd_vel"
ODOM_TOPIC        = "/rcr002/odom_uros"
CONNECT_TIMEOUT   = 5.0    # seconds to wait for subscriber

# Current config values
WHEEL_RADIUS_CURRENT    = 0.033
WHEEL_SEPARATION_CURRENT = 0.297

# ─── Bias Correction ───────────────────────────────────────────────────────────
# Software angular bias to compensate for hardware motor imbalance.
# Sign convention (ROS): positive angular.z = left turn (CCW from above)
#                        negative angular.z = right turn (CW from above)
# Robot veers LEFT → needs NEGATIVE bias to correct (push right).
# Tune empirically: start small, adjust by 0.05 increments until straight.
STRAIGHT_FWD_BIAS  = -0.65   # angular.z correction for forward straight moves
STRAIGHT_REV_BIAS  = -0.65   # angular.z correction for reverse straight moves (may differ)

# ─── Helpers ───────────────────────────────────────────────────────────────────

def wait_for_subscriber(node, pub, timeout=CONNECT_TIMEOUT):
    """Wait until twist_mux is subscribed before sending anything.
    Must spin the node so DDS discovery can run."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        rclpy.spin_once(node, timeout_sec=0.05)
        if pub.get_subscription_count() > 0:
            return True
    return False


def flush_stop(pub, count=5):
    """Publish zero-velocity burst to flush any stale Teensy state."""
    stop = Twist()
    for _ in range(count):
        pub.publish(stop)
        time.sleep(0.05)


def odom_position(msg):
    """Extract x, y from odom message."""
    return msg.pose.pose.position.x, msg.pose.pose.position.y


def odom_yaw(msg):
    """Extract yaw (radians) from odom message quaternion."""
    q = msg.pose.pose.orientation
    siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
    cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny_cosp, cosy_cosp)


# ─── Commands ──────────────────────────────────────────────────────────────────

def cmd_straight(distance_m):
    """Drive straight at constant speed. Report odom-measured distance."""
    if distance_m <= 0 or distance_m > 3.0:
        print("ERROR: distance must be between 0 and 3.0 m", file=sys.stderr)
        sys.exit(1)

    duration = distance_m / CAL_LINEAR_SPEED
    print(f"[CAL] Driving straight {distance_m:.3f} m at {CAL_LINEAR_SPEED} m/s (~{duration:.1f}s)")

    rclpy.init()
    node = Node("nine_cal_straight")
    pub  = node.create_publisher(Twist, CMD_VEL_TOPIC, 10)

    odom_start = [None]
    odom_end   = [None]

    def odom_cb(msg):
        if odom_start[0] is None:
            odom_start[0] = msg
        odom_end[0] = msg

    node.create_subscription(Odometry, ODOM_TOPIC, odom_cb, 10)

    # Wait for subscriber
    print(f"[CAL] Waiting for twist_mux subscriber on {CMD_VEL_TOPIC}...")
    if not wait_for_subscriber(node, pub):
        print("ERROR: No subscriber on /cmd_vel after timeout. Is twist_mux running?", file=sys.stderr)
        node.destroy_node()
        rclpy.shutdown()
        sys.exit(1)

    # Spin briefly to get initial odom reading
    for _ in range(10):
        rclpy.spin_once(node, timeout_sec=0.05)

    flush_stop(pub)

    # Wait for first odom message
    deadline = time.time() + 3.0
    while odom_start[0] is None and time.time() < deadline:
        rclpy.spin_once(node, timeout_sec=0.05)

    if odom_start[0] is None:
        print("WARNING: No odom data received. Odometry reporting unavailable.", file=sys.stderr)

    start_x, start_y = odom_position(odom_start[0]) if odom_start[0] else (0.0, 0.0)
    print(f"[CAL] Odom start: x={start_x:.4f} y={start_y:.4f}")
    print("[CAL] Moving... stand clear!")

    period   = 1.0 / PUBLISH_HZ
    start_t  = time.time()
    bias = STRAIGHT_FWD_BIAS if distance_m > 0 else STRAIGHT_REV_BIAS
    BIAS_DELAY = 0.5   # seconds before applying angular bias (let motors spin up first)
    if bias != 0.0:
        print(f"[CAL] Applying {'forward' if distance_m > 0 else 'reverse'} bias: angular.z={bias:.3f} (after {BIAS_DELAY}s delay)")

    while time.time() - start_t < duration:
        elapsed = time.time() - start_t
        twist = Twist()
        twist.linear.x = CAL_LINEAR_SPEED
        twist.angular.z = bias if elapsed >= BIAS_DELAY else 0.0
        pub.publish(twist)
        rclpy.spin_once(node, timeout_sec=0)
        time.sleep(period)

    # Stop
    flush_stop(pub)

    # Collect final odom
    for _ in range(20):
        rclpy.spin_once(node, timeout_sec=0.05)

    end_x, end_y = odom_position(odom_end[0]) if odom_end[0] else (start_x, start_y)
    odom_dist = math.sqrt((end_x - start_x) ** 2 + (end_y - start_y) ** 2)

    node.destroy_node()
    rclpy.shutdown()

    print()
    print("=" * 50)
    print(f"  Commanded distance : {distance_m:.3f} m")
    print(f"  Odom-reported dist : {odom_dist:.4f} m")
    print()
    print("  → Measure actual distance with tape measure")
    print(f"  → Then run: python3 nine_cal.py correct <actual_m> {distance_m:.3f}")
    print("=" * 50)


def cmd_spin(degrees):
    """Spin in place. Report odom-measured angle."""
    if degrees <= 0 or degrees > 720:
        print("ERROR: degrees must be between 0 and 720", file=sys.stderr)
        sys.exit(1)

    target_rad = math.radians(degrees)
    duration   = target_rad / CAL_ANGULAR_SPEED
    print(f"[CAL] Spinning {degrees:.1f}° ({target_rad:.3f} rad) at {CAL_ANGULAR_SPEED} rad/s (~{duration:.1f}s)")

    rclpy.init()
    node = Node("nine_cal_spin")
    pub  = node.create_publisher(Twist, CMD_VEL_TOPIC, 10)

    odom_msgs = []

    def odom_cb(msg):
        odom_msgs.append(msg)

    node.create_subscription(Odometry, ODOM_TOPIC, odom_cb, 10)

    print(f"[CAL] Waiting for twist_mux subscriber on {CMD_VEL_TOPIC}...")
    if not wait_for_subscriber(node, pub):
        print("ERROR: No subscriber on /cmd_vel after timeout.", file=sys.stderr)
        node.destroy_node()
        rclpy.shutdown()
        sys.exit(1)

    for _ in range(10):
        rclpy.spin_once(node, timeout_sec=0.05)

    flush_stop(pub)

    deadline = time.time() + 3.0
    while len(odom_msgs) == 0 and time.time() < deadline:
        rclpy.spin_once(node, timeout_sec=0.05)

    start_yaw = odom_yaw(odom_msgs[-1]) if odom_msgs else 0.0
    print(f"[CAL] Odom start yaw: {math.degrees(start_yaw):.2f}°")
    print("[CAL] Spinning... stand clear!")

    period  = 1.0 / PUBLISH_HZ
    start_t = time.time()
    twist   = Twist()
    twist.angular.z = CAL_ANGULAR_SPEED

    while time.time() - start_t < duration:
        pub.publish(twist)
        rclpy.spin_once(node, timeout_sec=0)
        time.sleep(period)

    flush_stop(pub)

    for _ in range(20):
        rclpy.spin_once(node, timeout_sec=0.05)

    end_yaw   = odom_yaw(odom_msgs[-1]) if odom_msgs else start_yaw
    # Handle yaw wrap-around for large rotations
    # We integrate angle differently — track cumulative spin by accumulating delta
    # For simplicity with odom start/end: compute shortest delta, note this may wrap
    raw_delta  = end_yaw - start_yaw
    # Normalize to [-pi, pi]
    while raw_delta >  math.pi: raw_delta -= 2 * math.pi
    while raw_delta < -math.pi: raw_delta += 2 * math.pi
    odom_deg  = abs(math.degrees(raw_delta))

    node.destroy_node()
    rclpy.shutdown()

    print()
    print("=" * 50)
    print(f"  Commanded rotation : {degrees:.1f}°")
    print(f"  Odom-reported rot  : {odom_deg:.2f}°")
    print()
    print("  → Measure actual rotation with tape/protractor")
    print(f"  → Then run: python3 nine_cal.py correct_spin <actual_deg> {degrees:.1f}")
    print("=" * 50)


def cmd_correct(actual_m, commanded_m):
    """Compute corrected wheel_radius from actual vs. commanded straight travel."""
    if commanded_m <= 0:
        print("ERROR: commanded_m must be positive", file=sys.stderr)
        sys.exit(1)

    correction_factor = actual_m / commanded_m
    new_radius        = WHEEL_RADIUS_CURRENT * correction_factor

    print()
    print("=" * 50)
    print("  Wheel Radius Correction")
    print(f"  Commanded   : {commanded_m:.4f} m")
    print(f"  Actual      : {actual_m:.4f} m")
    print(f"  Factor      : {correction_factor:.5f}  ({(correction_factor - 1) * 100:+.2f}%)")
    print()
    print(f"  Current wheel_radius : {WHEEL_RADIUS_CURRENT:.6f} m")
    print(f"  New     wheel_radius : {new_radius:.6f} m")
    print()
    print("  Update ~/ros2_ws/src/common_platform/config/my_controllers.yaml:")
    print(f"    wheel_radius: {new_radius:.6f}")
    print()
    print("  Then rebuild + restart:")
    print("    cd ~/ros2_ws && colcon build --packages-select common_platform")
    print("    sudo systemctl restart launch-robot.service")
    print("  And run calibration again to verify.")
    print("=" * 50)


def cmd_correct_spin(actual_deg, commanded_deg):
    """Compute corrected wheel_separation from actual vs. commanded rotation."""
    if commanded_deg <= 0:
        print("ERROR: commanded_deg must be positive", file=sys.stderr)
        sys.exit(1)

    correction_factor = commanded_deg / actual_deg   # inverse — wider sep = less rotation
    new_sep           = WHEEL_SEPARATION_CURRENT * correction_factor

    print()
    print("=" * 50)
    print("  Wheel Separation Correction")
    print(f"  Commanded   : {commanded_deg:.2f}°")
    print(f"  Actual      : {actual_deg:.2f}°")
    print(f"  Factor      : {correction_factor:.5f}  ({(correction_factor - 1) * 100:+.2f}%)")
    print()
    print(f"  Current wheel_separation : {WHEEL_SEPARATION_CURRENT:.6f} m")
    print(f"  New     wheel_separation : {new_sep:.6f} m")
    print()
    print("  Update ~/ros2_ws/src/common_platform/config/my_controllers.yaml:")
    print(f"    wheel_separation: {new_sep:.6f}")
    print()
    print("  Then rebuild + restart:")
    print("    cd ~/ros2_ws && colcon build --packages-select common_platform")
    print("    sudo systemctl restart launch-robot.service")
    print("  And run spin calibration again to verify.")
    print("=" * 50)


# ─── Main ──────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1].lower()

    if cmd == "straight":
        if len(sys.argv) != 3:
            print("Usage: nine_cal.py straight <distance_m>", file=sys.stderr)
            sys.exit(1)
        cmd_straight(float(sys.argv[2]))

    elif cmd == "spin":
        if len(sys.argv) != 3:
            print("Usage: nine_cal.py spin <degrees>", file=sys.stderr)
            sys.exit(1)
        cmd_spin(float(sys.argv[2]))

    elif cmd == "correct":
        if len(sys.argv) != 4:
            print("Usage: nine_cal.py correct <actual_m> <commanded_m>", file=sys.stderr)
            sys.exit(1)
        cmd_correct(float(sys.argv[2]), float(sys.argv[3]))

    elif cmd == "correct_spin":
        if len(sys.argv) != 4:
            print("Usage: nine_cal.py correct_spin <actual_deg> <commanded_deg>", file=sys.stderr)
            sys.exit(1)
        cmd_correct_spin(float(sys.argv[2]), float(sys.argv[3]))

    else:
        print(f"ERROR: Unknown command '{cmd}'", file=sys.stderr)
        print("Commands: straight, spin, correct, correct_spin", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

# Dependencies: rclpy, geometry_msgs, nav_msgs (all included with ROS2 kilted)
