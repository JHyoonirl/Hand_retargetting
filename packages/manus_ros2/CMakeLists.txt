cmake_minimum_required(VERSION 3.11)
project(manus_ros2)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# find dependencies
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(std_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(visualization_msgs REQUIRED)
find_package(manus_ros2_msgs REQUIRED)

add_executable(manus_data_publisher 
  src/manus_data_publisher.cpp
  src/ClientPlatformSpecific.cpp
  src/ManusDataPublisher.cpp)

add_executable(manus_glove_markers src/manus_glove_markers.cpp)
target_compile_features(manus_glove_markers PUBLIC cxx_std_17)
ament_target_dependencies(manus_glove_markers
  rclcpp geometry_msgs visualization_msgs manus_ros2_msgs)
set(MANUS_SDK_ROOT
  "${CMAKE_CURRENT_SOURCE_DIR}/../../vendor/manus/ManusSDK_v3.1.1/ROS2/ManusSDK"
  CACHE PATH "MANUS Linux SDK directory")
option(MANUS_INTEGRATED "Link the standalone Core Integrated SDK" ON)
if(MANUS_INTEGRATED)
  set(MANUS_LIBRARY_NAME ManusSDK_Integrated)
  target_compile_definitions(manus_data_publisher PRIVATE MANUS_INTEGRATED=1)
else()
  set(MANUS_LIBRARY_NAME ManusSDK)
endif()
set(MANUS_LIBRARY "${MANUS_SDK_ROOT}/lib/lib${MANUS_LIBRARY_NAME}.so")
if(NOT EXISTS "${MANUS_SDK_ROOT}/include/ManusSDK.h" OR NOT EXISTS "${MANUS_LIBRARY}")
  message(FATAL_ERROR "Missing proprietary MANUS SDK headers/library under ${MANUS_SDK_ROOT}")
endif()
find_package(Curses REQUIRED)
target_include_directories(manus_data_publisher PRIVATE
  "${MANUS_SDK_ROOT}/include" ${CURSES_INCLUDE_DIRS})
target_link_libraries(manus_data_publisher "${MANUS_LIBRARY}" ${CURSES_LIBRARIES})
target_compile_features(manus_data_publisher PUBLIC cxx_std_17)
install(TARGETS manus_data_publisher DESTINATION lib/${PROJECT_NAME})
install(TARGETS manus_glove_markers DESTINATION lib/${PROJECT_NAME})
install(FILES "${MANUS_LIBRARY}" DESTINATION lib/${PROJECT_NAME})
install(PROGRAMS client_scripts/manus_data_viz.py DESTINATION lib/${PROJECT_NAME})
install(DIRECTORY launch rviz DESTINATION share/${PROJECT_NAME})
set_target_properties(manus_data_publisher PROPERTIES INSTALL_RPATH "$ORIGIN")

ament_target_dependencies(manus_data_publisher rclcpp std_msgs geometry_msgs manus_ros2_msgs)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  # the following line skips the linter which checks for copyrights
  # comment the line when a copyright and license is added to all source files
  set(ament_cmake_copyright_FOUND TRUE)
  # the following line skips cpplint (only works in a git repo)
  # comment the line when this package is in a git repo and when
  # a copyright and license is added to all source files
  set(ament_cmake_cpplint_FOUND TRUE)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()
