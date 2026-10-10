# MANUS hardware configuration

This directory contains host-side configuration for the MANUS wireless dongle and glove.

- `udev/70-manus-hid.rules` is the project copy of the device permission rule.
- The rule must be installed on the host at `/etc/udev/rules.d/70-manus-hid.rules`; keeping it in this repository makes the setup reproducible.
- The vendor SDK is under `vendor/manus/ManusSDK_v3.1.1/` and the ROS 2 packages are under `ros2_ws/src/`.

Install or refresh the host rule from the project root with:

```bash
bash tools/install_udev_rules.sh
```

## Check both hands

The ROS topic index is discovery order, so use the message fields for hand identity:

```bash
source /opt/ros/jazzy/setup.bash
source ros2_ws/install/setup.bash
ros2 topic info /manus_glove_0
ros2 topic info /manus_glove_1
ros2 topic echo /manus_glove_0 --once
ros2 topic echo /manus_glove_1 --once
```

Find the right-hand message by its fields (`side: Right`, `hand_id: 1`) and the
left-hand message by (`side: Left`, `hand_id: 0`). A topic with `Publisher count:
0` means Core has not connected that glove yet; keep only one MANUS publisher
running, power on the glove and pair it to the dongle in MANUS Core. The current
Core settings use `autoPair: false`, so a newly added glove requires an explicit
pairing step.

## Pair a second wireless glove

The observed LED states are useful during setup: a solid blue LED generally
means the glove is already connected, while a blinking white LED indicates that
the glove is waiting to be paired. Stop the ROS publisher before starting the
official SDK client because Core Integrated supports one active client at a
time.

```bash
pkill -INT -f '/ros2_ws/install/manus_ros2/lib/manus_ros2/manus_data_publisher'
cd vendor/manus/ManusSDK_v3.1.1/SDKClient_Linux
./SDKClient_Linux.out
```

Choose `1` (`Core Integrated`), then press `P` in the main menu and `P` again
in `Glove Pairing` (`Pair first available Glove`). Keep the white-blinking glove
in pairing mode while doing this. After the success message, press `Q` to go
back and `Esc` to exit the SDK client. If no glove is available, re-enter the
glove's pairing mode and repeat the pairing command with the same dongle.

## Calibrate a glove

Run the project wrapper after stopping the ROS publisher and any Docker MANUS
container. It uses the SDK client stored inside this project and builds it
against the project copy of `libManusSDK_Integrated.so` if needed. The external
Downloads copy is only a fallback when the project SDK has been removed; use
`MANUS_SDK_CLIENT_ROOT` to select another SDK explicitly.

```bash
bash tools/manus_calibrate.sh
```

At the first prompt select `1` (`Core Integrated`). In the main menu press `C`
to open `Glove Calibration`. The SDK displays the required calibration steps:

1. Press `H` to choose the left or right glove.
2. Press `S` to start calibration.
3. Follow the currently displayed pose/instruction and press `E` to execute
   that step. Use `P` and `M` to move between steps.
4. Press `F` to finish the selected glove, then repeat for the other glove with
   `H` if both gloves are connected.
5. Press `K` to save the calibration and `Q`, then `Esc`, to exit.

The SDK saves the file as
`$HOME/Documents/manus-calibrations/Calibration.mcal` (or the directory named
by `XDG_DOCUMENTS_DIR`). Calibration requires a valid MANUS SDK/Integrated
license; a dongle alone cannot grant that license.

The wrapper refuses to start while `manus_data_publisher`, another SDK client,
or the Docker MANUS container is running because Core Integrated permits only
one active client at a time.
