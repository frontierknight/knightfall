#!/usr/bin/env bash
# Headless smoke test for the Gazebo tier: bring up Gazebo + TurtleBot3 + Nav2 with no GPU/display,
# then run tools/gz/smoke.py (lidar up, real-time factor, a Nav2 goal reached, ground truth read over
# gz-transport). Exits non-zero if any gate fails. Extra args are passed to smoke.py.
set -uo pipefail
source /opt/ros/jazzy/setup.bash
HERE="$(cd "$(dirname "$0")" && pwd)"
LOG="${KNIGHTFALL_LAUNCH_LOG:-/tmp/kf-launch.log}"

# Xvfb gives the sensor renderer (ogre2, gpu_lidar) a software GL context.
setsid xvfb-run -a -s "-screen 0 1280x1024x24" \
  ros2 launch nav2_bringup tb3_simulation_launch.py headless:=True use_rviz:=False >"$LOG" 2>&1 &
LAUNCH_PID=$!

cleanup() {
  kill -INT -- "-$LAUNCH_PID" 2>/dev/null
  sleep 5
  kill -KILL -- "-$LAUNCH_PID" 2>/dev/null
  pkill -KILL -f "gz sim" 2>/dev/null
  true
}
trap cleanup EXIT

timeout 600 python3 "$HERE/smoke.py" "$@"
rc=$?
if [ "$rc" -ne 0 ]; then
  echo "---- last 80 lines of launch log ($LOG) ----"
  tail -n 80 "$LOG"
fi
exit "$rc"
