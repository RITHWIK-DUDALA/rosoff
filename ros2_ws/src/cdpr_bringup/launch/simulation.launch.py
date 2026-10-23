#!/usr/bin/env python3
"""
Launch file for CDPR Full Simulation (Mode A).
Runs completely offline without physical hardware or micro-ROS agent.
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
        # 1. Robot State Publisher (URDF TF)
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name='robot_state_publisher',
            output='screen',
            parameters=[{'robot_description': robot_description_content}]
        ),

        # 2. Kinematics Node
        Node(
            package='cdpr_kinematics',
            executable='kinematics_node',
            name='cdpr_kinematics_node',
            output='screen',
            parameters=[params_file]
        ),

        # 3. Motion Planning Node
        Node(
            package='cdpr_motion',
            executable='motion_node',
            name='cdpr_motion_node',
            output='screen',
            parameters=[params_file]
        ),

        # 4. State Estimator Node
        Node(
            package='cdpr_state_estimator',
            executable='state_estimator_node',
            name='cdpr_state_estimator_node',
            output='screen'
        ),

        # 5. Simulation Driver Node
        Node(
            package='cdpr_hardware',
            executable='simulator_node',
            name='cdpr_simulator_node',
            output='screen'
        ),
    ])
