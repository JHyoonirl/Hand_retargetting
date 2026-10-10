from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    rviz_config = os.path.join(
        get_package_share_directory("manus_ros2"), "rviz", "manus_glove.rviz"
    )
    return LaunchDescription([
        Node(
            package="manus_ros2",
            executable="manus_glove_markers",
            name="manus_glove_markers",
            output="screen",
            parameters=[
                {
                    "glove_indexes": "0,1",
                    "frame_id": "manus",
                    "mirror_left": True,
                    "mirror_right": True,
                    "separate_hands": True,
                    "hand_separation": 0.24,
                }
            ],
        ),
        Node(
            package="rviz2",
            executable="rviz2",
            name="rviz2_manus_glove",
            arguments=["-d", rviz_config],
            output="screen",
        ),
    ])
