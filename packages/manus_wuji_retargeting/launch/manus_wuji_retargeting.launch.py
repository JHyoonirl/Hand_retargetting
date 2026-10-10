import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def _spawn_visualization(context):
    """Start URDF state publishing and optional RViz for dry-run output."""
    if LaunchConfiguration("visualize_dry_run").perform(context).lower() != "true":
        return []

    side = LaunchConfiguration("side").perform(context).lower()
    hand_name = LaunchConfiguration("hand_name").perform(context)
    description_share = get_package_share_directory("wuji_description")
    urdf_path = os.path.join(description_share, "urdf", f"{side}-ros.urdf")
    with open(urdf_path, "r", encoding="utf-8") as urdf_file:
        robot_description = urdf_file.read()

    actions = [
        Node(
            package="robot_state_publisher",
            executable="robot_state_publisher",
            name="robot_state_publisher",
            namespace=hand_name,
            parameters=[
                {"robot_description": ParameterValue(robot_description, value_type=str)},
                {"publish_frequency": 100.0},
            ],
            remappings=[("joint_states", "joint_states")],
            output="screen",
        )
    ]

    if LaunchConfiguration("rviz").perform(context).lower() == "true":
        rviz_path = os.path.join(description_share, "rviz", f"{side}.rviz")
        actions.append(
            Node(
                package="rviz2",
                executable="rviz2",
                name="rviz2",
                namespace=hand_name,
                arguments=["-d", rviz_path],
                output="screen",
            )
        )
    return actions


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument("side", default_value="right"),
        DeclareLaunchArgument("hand_name", default_value="hand_0"),
        DeclareLaunchArgument("control_rate", default_value="120.0"),
        DeclareLaunchArgument("dry_run", default_value="false"),
        DeclareLaunchArgument(
            "visualize_dry_run",
            default_value="false",
            description="Publish dry-run JointState and start the WUJI URDF state publisher",
        ),
        DeclareLaunchArgument(
            "rviz",
            default_value="false",
            description="Open RViz when visualize_dry_run is enabled",
        ),
        DeclareLaunchArgument("enable_on_start", default_value="true"),
        Node(
            package="manus_wuji_retargeting",
            executable="manus_wuji_retargeting",
            name="manus_wuji_retargeting",
            output="screen",
            emulate_tty=True,
            parameters=[{
                "side": LaunchConfiguration("side"),
                "hand_name": LaunchConfiguration("hand_name"),
                "control_rate": LaunchConfiguration("control_rate"),
                "dry_run": LaunchConfiguration("dry_run"),
                "visualize_dry_run": LaunchConfiguration("visualize_dry_run"),
                "enable_on_start": LaunchConfiguration("enable_on_start"),
            }],
        ),
        OpaqueFunction(function=_spawn_visualization),
    ])
