#!/usr/bin/env python3
"""
Launch file for starting micro-ROS Agent.
Supports Serial UART or UDP transports.
Default: Serial transport on /dev/ttyUSB0 (baud 115200).
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    transport_arg = DeclareLaunchArgument(
        'transport',
        default_value='serial',
        description='micro-ROS Agent transport type: serial or udp4'
    )
    dev_arg = DeclareLaunchArgument(
        'device',
        default_value='/dev/ttyUSB0',
        description='Serial device path (e.g. /dev/ttyUSB0 or COM3)'
    )
    baud_arg = DeclareLaunchArgument(
        'baudrate',
        default_value='115200',
        description='Serial baud rate'
    )

    return LaunchDescription([
        transport_arg,
        dev_arg,
        baud_arg,
        Node(
            package='micro_ros_agent',
            executable='micro_ros_agent',
            name='micro_ros_agent',
            output='screen',
            arguments=[
                LaunchConfiguration('transport'),
                '--dev', LaunchConfiguration('device'),
                '-b', LaunchConfiguration('baudrate')
            ]
        )
    ])
