from setuptools import setup
import os
from glob import glob

package_name = 'cdpr_bringup'

setup(
    name=package_name,
    version='1.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='CDPR Team',
    maintainer_email='robotics@example.com',
    description='Bringup and launch suite for 2-DOF Planar CDPR',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [],
    },
)
