#include <iostream>
#include <memory>
#include "rclcpp/rclcpp.hpp"
#include "ManusDataPublisher.hpp"
int main(int argc, char* argv[]) {
    rclcpp::init(argc, argv);
    int status = 0;
    try { rclcpp::spin(std::make_shared<ManusDataPublisher>()); }
    catch (const std::exception& e) { std::cerr << e.what() << std::endl; status = 1; }
    rclcpp::shutdown();
    return status;
}
