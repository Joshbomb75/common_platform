#!/bin/bash
# Wrapper for micro-ROS agent systemd service
# Sources ROS2 env before launching agent

source /opt/ros/kilted/setup.bash
source /home/rcr/ros2_ws/install/setup.bash

export FASTDDS_DEFAULT_PROFILES_FILE=/home/rcr/ros2_ws/super_client_configuration_file_rcr.xml
export ROS_DOMAIN_ID=0

exec /home/rcr/ros2_ws/install/micro_ros_agent/lib/micro_ros_agent/micro_ros_agent \
  serial \
  --dev /dev/serial/by-id/usb-Teensyduino_Dual_Serial_18268910-if00 \
  -v2
