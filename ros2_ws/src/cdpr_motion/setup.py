from setuptools import setup

package_name = 'cdpr_motion'

setup(
    name=package_name,
    version='1.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='CDPR Team',
    maintainer_email='robotics@example.com',
    description='Motion planning node for 2-DOF Planar CDPR',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'motion_node = cdpr_motion.motion_node:main',
        ],
    },
)
