#!/bin/bash
# Wrapper for FastDDS discovery server systemd service
# Sources ROS2 env so shared libraries are found

source /opt/ros/kilted/setup.bash

exec /opt/ros/kilted/bin/fastdds discovery -i 0 -l 127.0.0.1 -p 11811
