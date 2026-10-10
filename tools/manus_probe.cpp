#include "ManusSDK.h"
#include <atomic>
#include <chrono>
#include <iostream>
#include <thread>
#include <vector>
#include <cstring>
static std::atomic<unsigned> frames{0};
static std::atomic<bool> licensed{false};
static void landscape(const Landscape* const data) { licensed = data->settings.license.integrated; }
static void skeleton(const SkeletonStreamInfo* const data) {
    for (uint32_t i=0; i<data->skeletonsCount; ++i) {
        RawSkeletonInfo info{};
        if (CoreSdk_GetRawSkeletonInfo(i, &info) != SDKReturnCode_Success || !info.nodesCount) continue;
        std::vector<SkeletonNode> nodes(info.nodesCount);
        if (CoreSdk_GetRawSkeletonData(i, nodes.data(), info.nodesCount) == SDKReturnCode_Success) ++frames;
    }
}
static bool check(const char* name, SDKReturnCode result) {
    std::cout << name << "=" << static_cast<int>(result) << std::endl;
    return result == SDKReturnCode_Success;
}
int main(int argc, char** argv) {
    if (argc == 2 && std::strcmp(argv[1], "--help") == 0) {
        std::cout << "manus_probe: initialize Integrated SDK, connect, observe raw frames for 5 seconds.\n"
                     "Exit 0=licensed frames, 2=SDK failure, 3=no hosts, 4=no licensed frames.\n";
        return 0;
    }
    if (argc != 1) return 64;
    if (!check("initialize_integrated", CoreSdk_InitializeIntegrated())) return 2;
    struct Shutdown { ~Shutdown() { check("shutdown", CoreSdk_ShutDown()); } } shutdown;
    if (!check("landscape_callback", CoreSdk_RegisterCallbackForLandscapeStream(landscape)) ||
        !check("raw_callback", CoreSdk_RegisterCallbackForRawSkeletonStream(skeleton))) return 2;
    CoordinateSystemVUH coords{};
    CoordinateSystemVUH_Init(&coords);
    if (!check("coordinates", CoreSdk_InitializeCoordinateSystemWithVUH(coords, true))) return 2;
    if (!check("discover", CoreSdk_LookForHosts(2, false))) return 2;
    uint32_t count=0;
    if (!check("host_count", CoreSdk_GetNumberOfAvailableHostsFound(&count))) return 2;
    std::cout << "hosts=" << count << std::endl;
    if (!count) return 3;
    std::vector<ManusHost> hosts(count);
    if (!check("hosts", CoreSdk_GetAvailableHostsFound(hosts.data(), count)) ||
        !check("connect", CoreSdk_ConnectToHost(hosts.front()))) return 2;
    std::this_thread::sleep_for(std::chrono::seconds(5));
    std::cout << "integrated_license=" << licensed << " raw_frames=" << frames << std::endl;
    return licensed && frames ? 0 : 4;
}
