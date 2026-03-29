#!/usr/bin/env bash
# DEPLOY TO: ~/nine_scripts/nine_drive.sh
# FastDDS + micro-ROS agent are managed by systemd — no manual startup needed.
# Usage: bash nine_drive.sh <direction> <duration_seconds>

set -e

DIRECTION="${1:-forward}"
DURATION="${2:-1}"

source /opt/ros/kilted/setup.bash
source ~/ros2_ws/install/setup.bash
source ~/repos/common_platform/common_platform_ws/install/setup.bash 2>/dev/null || true

export FASTDDS_DEFAULT_PROFILES_FILE=~/ros2_ws/super_client_configuration_file_rcr.xml
export ROS_NAME=rcr002 ROS_NAMESPACE=/rcr002 ROS_DOMAIN_ID=0

echo "[nine_drive] Executing: $DIRECTION for ${DURATION}s"
python3 ~/nine_scripts/nine_move.py "$DIRECTION" "$DURATION"
