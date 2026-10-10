#!/usr/bin/env python3
"""MANUS raw skeleton -> Wuji Hand joint-command bridge.

MANUS publishes a 25-node skeleton.  The official wuji-hand-teleop pipeline
converts those nodes to the MediaPipe 21-point order and then calls the
official ``wuji-retargeting`` Retargeter.  This node keeps that conversion and
the side filtering, but publishes directly to the WUJI ROS 2 driver already in
this workspace.
"""

from __future__ import annotations

import os
import site
import sys
import threading
from pathlib import Path
from typing import Optional


def _bootstrap_python_environment() -> None:
    """Make the project .venv/vendor visible to ROS2's /usr/bin/python3.

    ROS2 console scripts use a fixed /usr/bin/python3 shebang even when a
    virtualenv is active. The project keeps retargeting dependencies in .venv,
    so add that site-packages directory and the vendored source explicitly.
    Docker installs the same package system-wide; these paths are harmless there.
    """
    candidates = []
    venv = os.environ.get("VIRTUAL_ENV")
    if venv:
        candidates.append(
            Path(venv) / "lib" /
            f"python{sys.version_info.major}.{sys.version_info.minor}" /
            "site-packages"
        )
    current = Path(__file__).resolve()
    for parent in (current, *current.parents):
        candidates.append(parent / "vendor" / "wuji-retargeting")
        candidates.append(parent.parent / "vendor" / "wuji-retargeting")
    seen = set()
    for candidate in candidates:
        candidate = candidate.resolve()
        if candidate in seen or not candidate.exists():
            continue
        seen.add(candidate)
        if candidate.is_dir() and candidate.name == "site-packages":
            site.addsitedir(str(candidate))
            if str(candidate) in sys.path:
                sys.path.remove(str(candidate))
            sys.path.insert(0, str(candidate))
        elif (candidate / "wuji_retargeting").is_dir():
            sys.path.insert(0, str(candidate))


_bootstrap_python_environment()

import numpy as np
import rclpy
from ament_index_python.packages import get_package_share_directory
from manus_ros2_msgs.msg import ManusGlove
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSHistoryPolicy, QoSReliabilityPolicy
from sensor_msgs.msg import JointState


# The ROS publisher preserves MANUS metadata (`chain_type` and `joint_type`).
# Use those labels instead of assuming a numeric node-ID layout: SDK 3.1.1
# currently emits IDs 0..24 (wrist/root + thumb, index, middle, ring, pinky),
# while older upstream examples used a different 1-based layout.
_MEDIAPIPE_LABELS = (
    ("wrist", ""),
    ("thumb", "mcp"), ("thumb", "pip"), ("thumb", "dip"), ("thumb", "tip"),
    ("index", "pip"), ("index", "ip"), ("index", "dip"), ("index", "tip"),
    ("middle", "pip"), ("middle", "ip"), ("middle", "dip"), ("middle", "tip"),
    ("ring", "pip"), ("ring", "ip"), ("ring", "dip"), ("ring", "tip"),
    ("pinky", "pip"), ("pinky", "ip"), ("pinky", "dip"), ("pinky", "tip"),
)
_CHAIN_ALIASES = {
    "thumb": "thumb",
    "fingerthumb": "thumb",
    "index": "index",
    "fingerindex": "index",
    "middle": "middle",
    "fingermiddle": "middle",
    "ring": "ring",
    "fingerring": "ring",
    "pinky": "pinky",
    "fingerpinky": "pinky",
    "hand": "wrist",
}
_JOINT_ALIASES = {
    "invalid": "",
    "mcp": "mcp",
    "metacarpal": "mcp",
    "pip": "pip",
    "proximal": "pip",
    "ip": "ip",
    "intermediate": "ip",
    "dip": "dip",
    "distal": "dip",
    "tip": "tip",
}


def _node_label(node: ManusGlove) -> Optional[tuple[str, str]]:
    """Return a stable semantic label for one MANUS raw node."""
    chain = str(node.chain_type).strip().lower().replace("_", "")
    joint = str(node.joint_type).strip().lower().replace("_", "")
    chain_name = _CHAIN_ALIASES.get(chain)
    joint_name = _JOINT_ALIASES.get(joint)
    if chain_name is None or joint_name is None:
        return None
    if chain_name == "wrist":
        return ("wrist", "")
    return (chain_name, joint_name)


def manus_to_mediapipe(msg: ManusGlove) -> Optional[np.ndarray]:
    """Convert one MANUS message to the 21x3 input expected by Retargeter.

    MANUS non-thumb fingers expose an extra metacarpal point before the four
    landmarks used by the upstream WUJI MANUS adapter.  Map MANUS
    PIP/IP/DIP/TIP to MediaPipe MCP/PIP/DIP/TIP and omit that leading MANUS
    MCP point.  The wrist is the raw node whose chain is ``Hand`` and joint is
    ``Invalid``.
    """
    positions: dict[tuple[str, str], np.ndarray] = {}
    for node in msg.raw_nodes:
        label = _node_label(node)
        if label is None or label in positions:
            continue
        positions[label] = np.asarray(
            [node.pose.position.x, -node.pose.position.y, node.pose.position.z],
            dtype=np.float64,
        )

    missing = [label for label in _MEDIAPIPE_LABELS if label not in positions]
    if missing:
        return None
    return np.asarray([positions[label] for label in _MEDIAPIPE_LABELS], dtype=np.float64)


def _best_effort_qos() -> QoSProfile:
    return QoSProfile(
        reliability=QoSReliabilityPolicy.BEST_EFFORT,
        history=QoSHistoryPolicy.KEEP_LAST,
        depth=1,
    )


class ManusWujiRetargeting(Node):
    """One-side MANUS subscriber and WUJI command publisher."""

    def __init__(self) -> None:
        super().__init__("manus_wuji_retargeting")

        self.declare_parameter("side", "right")
        self.declare_parameter("hand_name", "hand_0")
        self.declare_parameter("manus_topic_0", "/manus_glove_0")
        self.declare_parameter("manus_topic_1", "/manus_glove_1")
        self.declare_parameter("control_rate", 120.0)
        self.declare_parameter("dry_run", False)
        self.declare_parameter("visualize_dry_run", False)
        self.declare_parameter("enable_on_start", True)
        self.declare_parameter("retarget_config", "")

        self.side = str(self.get_parameter("side").value).lower()
        if self.side not in ("left", "right"):
            raise ValueError("side must be 'left' or 'right'")
        self.hand_name = str(self.get_parameter("hand_name").value)
        self.dry_run = bool(self.get_parameter("dry_run").value)
        self.visualize_dry_run = bool(self.get_parameter("visualize_dry_run").value)
        if self.visualize_dry_run and not self.dry_run:
            raise ValueError("visualize_dry_run requires dry_run:=true")
        self.control_rate = float(self.get_parameter("control_rate").value)
        if self.control_rate <= 0.0:
            raise ValueError("control_rate must be greater than zero")

        config_parameter = str(self.get_parameter("retarget_config").value)
        if config_parameter:
            config_path = Path(config_parameter).expanduser().resolve()
        else:
            config_path = (
                Path(get_package_share_directory("manus_wuji_retargeting"))
                / "config"
                / f"retarget_manus_{self.side}.yaml"
            )
        if not config_path.exists():
            raise FileNotFoundError(f"MANUS retarget config not found: {config_path}")

        try:
            from wuji_retargeting import Retargeter
        except ImportError as exc:
            raise RuntimeError(
                "wuji-retargeting is not installed. Run "
                "bash tools/install_wuji_retargeting.sh"
            ) from exc

        self.retargeter = Retargeter.from_yaml(str(config_path), self.side)
        if self.retargeter.num_joints != 20:
            raise RuntimeError(
                f"Retargeter returned {self.retargeter.num_joints} joints; expected 20"
            )

        self.command_publisher = self.create_publisher(
            JointState,
            f"/{self.hand_name}/joint_commands",
            _best_effort_qos(),
        )
        self._visualization_publisher = None
        self._visualization_joint_names = list(
            self.retargeter.optimizer.robot.dof_joint_names
        )
        if len(self._visualization_joint_names) != self.retargeter.num_joints:
            raise RuntimeError(
                "Retargeter joint-name count does not match its joint vector: "
                f"{len(self._visualization_joint_names)} != "
                f"{self.retargeter.num_joints}"
            )
        if self.visualize_dry_run:
            self._visualization_publisher = self.create_publisher(
                JointState,
                f"/{self.hand_name}/joint_states",
                _best_effort_qos(),
            )
        manus_qos = _best_effort_qos()
        self._manus_subscriptions = [
            self.create_subscription(
                ManusGlove,
                str(self.get_parameter("manus_topic_0").value),
                self._on_manus,
                manus_qos,
            ),
            self.create_subscription(
                ManusGlove,
                str(self.get_parameter("manus_topic_1").value),
                self._on_manus,
                manus_qos,
            ),
        ]

        self._latest_keypoints: Optional[np.ndarray] = None
        self._keypoint_lock = threading.Lock()
        self._received_frames = 0
        self._published_commands = 0
        self._published_visualizations = 0
        self._warned_missing_nodes = False
        self._valid_frame_logged = False

        # The WUJI driver starts enabled by default, but it can have been
        # disabled by the previous safety/test command.  Re-enable this hand
        # when requested so a new retargeting session is immediately usable.
        self._enable_future = None
        self._enable_client = None
        if bool(self.get_parameter("enable_on_start").value) and not self.dry_run:
            try:
                from wujihand_msgs.srv import SetEnabled

                self._enable_client = self.create_client(
                    SetEnabled, f"/{self.hand_name}/set_enabled"
                )
                self._enable_request_type = SetEnabled.Request
            except ImportError:
                self.get_logger().warning(
                    "wujihand_msgs is unavailable; skipping automatic motor enable"
                )
                self._enable_client = None

        self.create_timer(1.0 / self.control_rate, self._publish_latest)
        self.create_timer(1.0, self._status)

        self.get_logger().info(
            f"MANUS -> Wuji retargeting ready: side={self.side}, "
            f"/manus_glove_0,/manus_glove_1 -> /{self.hand_name}/joint_commands "
            f"at {self.control_rate:.1f} Hz"
        )
        self.get_logger().info(f"Retarget config: {config_path}")
        if self.dry_run:
            message = "dry_run=true: commands will be calculated but not sent to WUJI"
            if self.visualize_dry_run:
                message += "; publishing JointState for RViz"
            self.get_logger().warning(message)

    def _on_manus(self, msg: ManusGlove) -> None:
        if str(msg.side).strip().lower() != self.side:
            return
        keypoints = manus_to_mediapipe(msg)
        if keypoints is None:
            if not self._warned_missing_nodes:
                present = sorted(
                    str(_node_label(node)) for node in msg.raw_nodes
                    if _node_label(node) is not None
                )
                self.get_logger().warning(
                    f"MANUS {self.side} frame is missing semantic nodes; "
                    f"present={present}"
                )
                self._warned_missing_nodes = True
            return
        with self._keypoint_lock:
            self._latest_keypoints = keypoints
        self._received_frames += 1
        if not self._valid_frame_logged:
            self.get_logger().info(
                f"First valid {self.side} MANUS frame received ({len(msg.raw_nodes)} raw nodes)"
            )
            self._valid_frame_logged = True

    def _publish_latest(self) -> None:
        self._request_enable_once()
        with self._keypoint_lock:
            keypoints = self._latest_keypoints
            self._latest_keypoints = None
        if keypoints is None:
            return
        try:
            positions = np.asarray(self.retargeter.retarget(keypoints), dtype=np.float64)
        except Exception as exc:  # keep the ROS node alive on a bad frame
            self.get_logger().error(f"MANUS {self.side} retargeting failed: {exc}")
            return
        if positions.shape != (20,) or not np.all(np.isfinite(positions)):
            self.get_logger().error(f"Retargeter returned invalid joint vector: {positions.shape}")
            return
        if self.dry_run:
            if self._visualization_publisher is not None:
                visualization = JointState()
                visualization.header.stamp = self.get_clock().now().to_msg()
                visualization.name = self._visualization_joint_names
                visualization.position = positions.tolist()
                self._visualization_publisher.publish(visualization)
                self._published_visualizations += 1
            return
        command = JointState()
        command.header.stamp = self.get_clock().now().to_msg()
        command.name = self._visualization_joint_names
        command.position = positions.tolist()
        self.command_publisher.publish(command)
        self._published_commands += 1

    def _request_enable_once(self) -> None:
        if self._enable_client is None or self._enable_future is not None:
            return
        if not self._enable_client.service_is_ready():
            return
        request = self._enable_request_type()
        request.finger_id = 255
        request.joint_id = 255
        request.enabled = True
        self._enable_future = self._enable_client.call_async(request)
        self.get_logger().info(f"Requested enable for all joints on /{self.hand_name}")

    def _status(self) -> None:
        if self._enable_future is not None and self._enable_future.done():
            try:
                response = self._enable_future.result()
                self.get_logger().info(f"WUJI enable: {response.message}")
            except Exception as exc:
                self.get_logger().error(f"WUJI enable service failed: {exc}")
            self._enable_future = None
        if self._received_frames == 0:
            self.get_logger().warning(
                f"No {self.side} MANUS frame received yet; check the MANUS license and topics"
            )
        elif self._published_commands == 0 and not self.dry_run:
            self.get_logger().warning("MANUS frames received, but no WUJI commands published yet")
        elif self.visualize_dry_run and self._published_visualizations == 0:
            self.get_logger().warning("MANUS frames received, but no RViz JointState published yet")


def main(args=None) -> None:
    rclpy.init(args=args)
    node = ManusWujiRetargeting()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        if rclpy.ok():
            node.destroy_node()
            rclpy.shutdown()


if __name__ == "__main__":
    main()
