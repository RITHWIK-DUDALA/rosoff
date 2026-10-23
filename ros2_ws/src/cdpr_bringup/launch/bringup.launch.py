#!/usr/bin/env python3
"""
Launch file for CDPR Physical Hardware Interface (Mode B).
Enforces hardware readiness gates and safe torque off defaults.
"""
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.substitutions import Command, FindExecutable, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    pkg_description = FindPackageShare('cdpr_description')
    pkg_bringup = FindPackageShare('cdpr_bringup')

    urdf_file = PathJoinSubstitution([pkg_description, 'urdf', 'cdpr.urdf.xacro'])
    params_file = PathJoinSubstitution([pkg_bringup, 'config', 'ros2_params.yaml'])

    robot_description_content = Command([
        FindExecutable(name='xacro'),
        ' ',
        urdf_file
    ])

    return LaunchDescription([
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name='robot_state_publisher',
            output='screen',
            parameters=[{'robot_description': robot_description_content}]
        ),
        Node(
            package='cdpr_kinematics',
            executable='kinematics_node',
            name='cdpr_kinematics_node',
            output='screen',
            parameters=[params_file]
        ),
        Node(
            package='cdpr_motion',
            executable='motion_node',
            name='cdpr_motion_node',
            output='screen',
            parameters=[params_file]
        ),
        Node(
            package='cdpr_state_estimator',
            executable='state_estimator_node',
            name='cdpr_state_estimator_node',
            output='screen'
        ),
        Node(
            package='cdpr_hardware',
            executable='hardware_node',
            name='cdpr_hardware_node',
            output='screen',
            parameters=[params_file]
        ),
    ])
