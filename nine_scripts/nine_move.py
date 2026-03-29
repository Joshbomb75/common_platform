# DEPLOY TO: ~/nine_scripts/nine_move.py
#!/usr/bin/env python3
"""
Nine's movement script — S-curve velocity ramping, safe startup.
Usage: python3 nine_move.py <direction> <duration_seconds>
Directions: forward, backward, left, right, stop

Velocity pipeline: /cmd_vel → twist_mux → /rcr002/cmd_vel → Teensy
Startup: waits for confirmed subscriber, sends stop flush before any motion.
Max duration: 5.0 seconds (safety cap).
Prints MOVE_OK on success.

Ramp profile: sinusoidal S-curve (cosine interpolation).
  - Zero jerk at start and end of ramp — no snap or lurch
  - Ramp up: 0.6s, Ramp down: 0.5s
  - This is Phase 0 scaffolding; nav2_velocity_smoother replaces it in Phase 2
"""

import sys
import math
import time
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist

LINEAR_SPEED    = 0.3    # m/s
ANGULAR_SPEED   = 1.2    # rad/s
PUBLISH_HZ      = 20.0
MAX_DURATION    = 5.0
RAMP_UP_S       = 0.7    # seconds — longer = gentler acceleration
RAMP_DOWN_S     = 0.8    # seconds — longer = gentler deceleration (extra: reduces forward caster rock)
CONNECT_TIMEOUT = 3.0    # max seconds to wait for subscriber

CMD_VEL_TOPIC = "/cmd_vel"

DIRECTION_MAP = {
    "forward":  ( LINEAR_SPEED,  0.0),
    "backward": (-LINEAR_SPEED,  0.0),
    "left":     ( 0.0,           ANGULAR_SPEED),
    "right":    ( 0.0,          -ANGULAR_SPEED),
    "stop":     ( 0.0,           0.0),
}


def scurve_scale(t, duration, ramp_up, ramp_down):
    """
    S-curve velocity profile using cosine interpolation.

    Returns a scale factor in [0.0, 1.0]:
      - Ramp-up phase:   smooth 0 → 1 using (1 - cos(π·t/ramp_up)) / 2
      - Cruise phase:    constant 1.0
      - Ramp-down phase: smooth 1 → 0 using (1 + cos(π·t/ramp_down)) / 2

    Unlike a linear ramp (trapezoidal), this has zero jerk at the corners —
    no sudden snap when acceleration starts or ends.
    """
    if duration <= 0:
        return 1.0

    # Clamp ramps so they don't overlap
    ramp_up   = min(ramp_up,   duration / 2.0)
    ramp_down = min(ramp_down, duration / 2.0)

    if t < 0:
        return 0.0
    if t >= duration:
        return 0.0

    if t < ramp_up:
        # Rising S: 0 → 1
        return (1.0 - math.cos(math.pi * t / ramp_up)) / 2.0

    if t > duration - ramp_down:
        # Falling S: 1 → 0
        t_into_ramp = t - (duration - ramp_down)
        return (1.0 + math.cos(math.pi * t_into_ramp / ramp_down)) / 2.0

    return 1.0  # cruise


def main():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <direction> <duration_seconds>", file=sys.stderr)
        print(f"Directions: {', '.join(DIRECTION_MAP.keys())}", file=sys.stderr)
        sys.exit(1)

    direction = sys.argv[1].lower()
    try:
        duration = float(sys.argv[2])
    except ValueError:
        print("ERROR: duration must be a number", file=sys.stderr)
        sys.exit(1)

    if direction not in DIRECTION_MAP:
        print(f"ERROR: Unknown direction '{direction}'. Valid: {', '.join(DIRECTION_MAP.keys())}", file=sys.stderr)
        sys.exit(1)
    if duration > MAX_DURATION:
        print(f"ERROR: Duration {duration}s exceeds safety cap of {MAX_DURATION}s", file=sys.stderr)
        sys.exit(1)
    if duration < 0:
        print("ERROR: Duration must be non-negative", file=sys.stderr)
        sys.exit(1)

    lin_x, ang_z = DIRECTION_MAP[direction]

    rclpy.init()
    node = Node("nine_move")
    pub  = node.create_publisher(Twist, CMD_VEL_TOPIC, 10)

    # Wait for confirmed subscriber (twist_mux must be connected)
    # spin_once() is required to drive DDS discovery; without it, get_subscription_count() never updates
    deadline = time.time() + CONNECT_TIMEOUT
    while pub.get_subscription_count() == 0 and time.time() < deadline:
        rclpy.spin_once(node, timeout_sec=0.05)

    if pub.get_subscription_count() == 0:
        print("ERROR: No subscriber on /cmd_vel after timeout — is twist_mux running?", file=sys.stderr)
        node.destroy_node()
        rclpy.shutdown()
        sys.exit(1)

    # Flush any stale Teensy state before moving
    stop = Twist()
    for _ in range(5):
        pub.publish(stop)
        time.sleep(0.05)

    if direction == "stop":
        print("MOVE_OK")
        node.destroy_node()
        rclpy.shutdown()
        sys.exit(0)

    # Execute move with S-curve ramp profile
    period = 1.0 / PUBLISH_HZ
    start  = time.time()

    while True:
        elapsed = time.time() - start
        if elapsed >= duration:
            break
        scale = scurve_scale(elapsed, duration, RAMP_UP_S, RAMP_DOWN_S)
        twist = Twist()
        twist.linear.x  = lin_x * scale
        twist.angular.z = ang_z * scale
        pub.publish(twist)
        time.sleep(period)

    # Final stop burst
    for _ in range(5):
        pub.publish(stop)
        time.sleep(0.05)

    node.destroy_node()
    rclpy.shutdown()
    print("MOVE_OK")
    sys.exit(0)


if __name__ == "__main__":
    main()

# Dependencies: rclpy, geometry_msgs (included with ROS2 kilted)
