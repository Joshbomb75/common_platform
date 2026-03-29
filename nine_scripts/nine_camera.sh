#!/usr/bin/env bash
# DEPLOY TO: ~/nine_scripts/nine_camera.sh
# Nine's camera launcher — manages full lifecycle: kill strays, launch, snap, cleanup.
# Usage: source ~/.profile && bash ~/nine_scripts/nine_camera.sh
# Output: SNAP_OK:/tmp/nine_snap.jpg on success, exits 1 on failure

# Source full ROS2 environment
source /opt/ros/kilted/setup.bash
source ~/ros2_ws/install/setup.bash
source ~/repos/common_platform/common_platform_ws/install/setup.bash

# ROS env vars (needed for non-interactive SSH sessions)
export ROS_NAME=rcr002
export ROS_NAMESPACE=/rcr002
export ROS_DOMAIN_ID=0
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
# Unset the super-client profile — it requires a running discovery server which may not be up.
# Default UDP multicast discovery works fine for local single-machine use.
unset FASTDDS_DEFAULT_PROFILES_FILE

# Kill any stray camera processes holding the libcamera device
pkill -f camera_node 2>/dev/null || true
sleep 2

# Launch camera in background (inherits full env from this shell)
ros2 launch sensors camera.launch.py &>/tmp/camera_launch.log &
CAM_PID=$!

# Trap cleanup — always kill camera on exit
cleanup() {
    kill $CAM_PID 2>/dev/null
    wait $CAM_PID 2>/dev/null
}
trap cleanup EXIT

# Wait for camera node to initialize and start publishing
sleep 8

# Grab the frame — nine_snap.py subscribes directly, no self-launch logic
python3 ~/nine_scripts/nine_snap.py
