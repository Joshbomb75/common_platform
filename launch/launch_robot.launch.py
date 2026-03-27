import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import GroupAction
from launch.substitutions import Command
from launch_ros.actions import Node, PushRosNamespace


def generate_launch_description():

    package_name = 'common_platform'

    rsp = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[{
            'robot_description': Command([
                'xacro ',
                os.path.join(get_package_share_directory(package_name),
                             'description', 'common_platform.urdf.xacro'),
                ' use_ros2_control:=false sim_mode:=false'
            ]),
            'use_sim_time': False,
        }]
    )

    twist_mux_params = os.path.join(
        get_package_share_directory(package_name), 'config', 'twist_mux.yaml')
    twist_mux = Node(
        package='twist_mux',
        executable='twist_mux',
        parameters=[twist_mux_params],
        remappings=[('/cmd_vel_out', '/rcr002/cmd_vel_mux')]
    )

    vel_smoother_params = os.path.join(
        get_package_share_directory(package_name), 'config', 'velocity_smoother.yaml')
    vel_smoother = Node(
        package='nav2_velocity_smoother',
        executable='velocity_smoother',
        name='velocity_smoother',
        output='screen',
        parameters=[vel_smoother_params],
        remappings=[
            ('cmd_vel', '/rcr002/cmd_vel_mux'),
            ('cmd_vel_smoothed', '/rcr002/cmd_vel'),
        ]
    )

    odom_tf = Node(
        package='common_platform',
        executable='odom_tf_broadcaster',
        name='odom_tf_broadcaster',
        output='screen',
    )

    ns = os.environ.get('ROS_NAMESPACE', '').strip()
    if ns:
        return LaunchDescription([
            GroupAction([
                PushRosNamespace(ns),
                rsp,
                twist_mux,
                vel_smoother,
                odom_tf,
            ])
        ])
    else:
        return LaunchDescription([
            rsp,
            twist_mux,
            vel_smoother,
            odom_tf,
        ])
