#include <algorithm>
#include <chrono>
#include <cstdint>
#include <map>
#include <mutex>
#include <sstream>
#include <string>
#include <unordered_map>
#include <vector>

#include "geometry_msgs/msg/point.hpp"
#include "manus_ros2_msgs/msg/manus_glove.hpp"
#include "rclcpp/rclcpp.hpp"
#include "visualization_msgs/msg/marker.hpp"
#include "visualization_msgs/msg/marker_array.hpp"

class ManusGloveMarkers final : public rclcpp::Node
{
public:
  ManusGloveMarkers()
  : Node("manus_glove_markers")
  {
    declare_parameter<std::string>("glove_indexes", "0,1");
    declare_parameter<std::string>("frame_id", "manus");
    declare_parameter<bool>("mirror_left", true);
    declare_parameter<bool>("mirror_right", true);
    declare_parameter<bool>("separate_hands", true);
    declare_parameter<double>("hand_separation", 0.24);

    frame_id_ = get_parameter("frame_id").as_string();
    mirror_left_ = get_parameter("mirror_left").as_bool();
    mirror_right_ = get_parameter("mirror_right").as_bool();
    separate_hands_ = get_parameter("separate_hands").as_bool();
    hand_separation_ = get_parameter("hand_separation").as_double();
    const auto indexes = get_parameter("glove_indexes").as_string();
    std::stringstream stream(indexes);
    std::string index;
    while (std::getline(stream, index, ',')) {
      if (index.empty()) {
        continue;
      }
      const auto glove_index = std::stoi(index);
      const auto topic = "/manus_glove_" + std::to_string(glove_index);
      subscriptions_.push_back(create_subscription<manus_ros2_msgs::msg::ManusGlove>(
        topic, rclcpp::SensorDataQoS(),
        [this](const manus_ros2_msgs::msg::ManusGlove::SharedPtr message) {
          if (message == nullptr) {
            return;
          }
          std::lock_guard<std::mutex> lock(latest_messages_mutex_);
          latest_messages_[message->glove_id] = *message;
        }));
      RCLCPP_INFO(get_logger(), "Subscribing to %s", topic.c_str());
    }

    marker_publisher_ = create_publisher<visualization_msgs::msg::MarkerArray>(
      "/manus_glove_markers", rclcpp::QoS(rclcpp::KeepLast(1)).reliable());
    marker_timer_ = create_wall_timer(
      std::chrono::milliseconds(8), [this]() { publish_latest_markers(); });
  }

private:
  void publish_latest_markers()
  {
    std::map<uint32_t, manus_ros2_msgs::msg::ManusGlove> messages;
    {
      std::lock_guard<std::mutex> lock(latest_messages_mutex_);
      messages = latest_messages_;
    }
    if (messages.empty()) {
      return;
    }

    visualization_msgs::msg::MarkerArray markers;
    const auto stamp = now();
    for (const auto & entry : messages) {
      append_markers(entry.second, stamp, markers);
    }
    marker_publisher_->publish(markers);
  }

  void append_markers(
    const manus_ros2_msgs::msg::ManusGlove & message,
    const rclcpp::Time & stamp,
    visualization_msgs::msg::MarkerArray & markers)
  {
    const bool mirror =
      (mirror_left_ && message.side == "Left") ||
      (mirror_right_ && message.side == "Right");
    double hand_offset_x = 0.0;
    if (separate_hands_) {
      if (message.side == "Left") {
        // With the default RViz yaw, +x is rendered on the left side of the
        // screen. Put the anatomical left hand on the screen left.
        hand_offset_x = 0.5 * hand_separation_;
      } else if (message.side == "Right") {
        hand_offset_x = -0.5 * hand_separation_;
      }
    }
    auto display_point = [mirror, hand_offset_x](const geometry_msgs::msg::Point & point) {
      auto result = point;
      if (mirror) {
        // MANUS left-hand samples arrive with the lateral hand axis opposite
        // to the palm-facing RViz view. This is display-only; the ROS message
        // remains unchanged for retargeting consumers.
        result.x = -result.x;
      }
      // Separate the two display copies without changing the source ROS data.
      result.x += hand_offset_x;
      return result;
    };

    const auto ns = "manus_glove_" + std::to_string(message.glove_id);

    visualization_msgs::msg::Marker joints;
    joints.header.frame_id = frame_id_;
    joints.header.stamp = stamp;
    joints.ns = ns;
    joints.id = 0;
    joints.type = visualization_msgs::msg::Marker::SPHERE_LIST;
    joints.action = visualization_msgs::msg::Marker::ADD;
    joints.pose.orientation.w = 1.0;
    joints.scale.x = 0.012;
    joints.scale.y = 0.012;
    joints.scale.z = 0.012;
    joints.color.r = 0.10F;
    joints.color.g = 0.80F;
    joints.color.b = 1.00F;
    joints.color.a = 1.00F;

    std::unordered_map<int32_t, geometry_msgs::msg::Point> points;
    for (const auto & node : message.raw_nodes) {
      const auto point = display_point(node.pose.position);
      joints.points.push_back(point);
      points[node.node_id] = point;
    }

    visualization_msgs::msg::Marker bones;
    bones.header = joints.header;
    bones.ns = ns;
    bones.id = 1;
    bones.type = visualization_msgs::msg::Marker::LINE_LIST;
    bones.action = visualization_msgs::msg::Marker::ADD;
    bones.pose.orientation.w = 1.0;
    bones.scale.x = 0.004;
    bones.color.r = 1.00F;
    bones.color.g = 0.55F;
    bones.color.b = 0.05F;
    bones.color.a = 1.00F;

    for (const auto & node : message.raw_nodes) {
      if (node.parent_node_id == node.node_id) {
        continue;
      }
      const auto parent = points.find(node.parent_node_id);
      if (parent == points.end()) {
        continue;
      }
      bones.points.push_back(parent->second);
      bones.points.push_back(display_point(node.pose.position));
    }

    // Keep the anatomical side visible in RViz. The MANUS SDK already
    // supplies this value; the marker bridge must not infer left/right from
    // the camera view or mirror the raw coordinates.
    visualization_msgs::msg::Marker side_label;
    side_label.header = joints.header;
    side_label.ns = ns;
    side_label.id = 2;
    side_label.type = visualization_msgs::msg::Marker::TEXT_VIEW_FACING;
    side_label.action = visualization_msgs::msg::Marker::ADD;
    side_label.pose.orientation.w = 1.0;
    side_label.scale.z = 0.035;
    if (message.side == "Left") {
      side_label.color.r = 0.20F;
      side_label.color.g = 0.85F;
      side_label.color.b = 1.00F;
    } else if (message.side == "Right") {
      side_label.color.r = 1.00F;
      side_label.color.g = 0.55F;
      side_label.color.b = 0.10F;
    } else {
      side_label.color.r = 0.95F;
      side_label.color.g = 0.95F;
      side_label.color.b = 0.95F;
    }
    side_label.color.a = 1.00F;
    side_label.text = message.side + " (hand_id " + std::to_string(message.hand_id) + ")";
    if (!message.raw_nodes.empty()) {
      auto label_anchor = display_point(message.raw_nodes.front().pose.position);
      for (const auto & node : message.raw_nodes) {
        const auto point = display_point(node.pose.position);
        if (point.z > label_anchor.z) {
          label_anchor = point;
        }
      }
      side_label.pose.position = label_anchor;
      side_label.pose.position.z += 0.04;
    }

    markers.markers.push_back(std::move(joints));
    markers.markers.push_back(std::move(bones));
    markers.markers.push_back(std::move(side_label));
  }

  std::string frame_id_;
  bool mirror_left_{true};
  bool mirror_right_{true};
  bool separate_hands_{true};
  double hand_separation_{0.24};
  rclcpp::Publisher<visualization_msgs::msg::MarkerArray>::SharedPtr marker_publisher_;
  rclcpp::TimerBase::SharedPtr marker_timer_;
  std::mutex latest_messages_mutex_;
  std::map<uint32_t, manus_ros2_msgs::msg::ManusGlove> latest_messages_;
  std::vector<rclcpp::Subscription<manus_ros2_msgs::msg::ManusGlove>::SharedPtr> subscriptions_;
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<ManusGloveMarkers>());
  rclcpp::shutdown();
  return 0;
}
