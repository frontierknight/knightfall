#!/usr/bin/env bash
# Knightfall deliverable ① — acceptance test (draft; validate on the box).
# Proves: legitimate secured comms succeed; an unauthorized participant is denied.
#   Case A: secured diag_publisher -> secured maintenance_listener  ==> listener RECEIVES.
#   Case B: unauthorized listener (no creds) on the secured domain  ==> listener RECEIVES NOTHING.
set -o pipefail
source /opt/ros/humble/setup.bash

HERE="$(cd "$(dirname "$0")" && pwd)"
KS="$HOME/knightfall_keystore"
export ROS_DOMAIN_ID=42
export ROS_SECURITY_KEYSTORE="$KS"
export ROS_SECURITY_ENABLE=true
export ROS_SECURITY_STRATEGY=Enforce
TOPIC=diagnostics
RUN=6            # seconds per case
OUT=$(mktemp -d)

echo "== [setup] keystore + artifacts =="
rm -rf "$KS"
ros2 security create_keystore "$KS" >/dev/null
ros2 security generate_artifacts -k "$KS" \
  -p "$HERE/policy/knightfall_diag.policy.xml" \
  -e /diag_publisher /maintenance_listener >/dev/null
echo "  enclaves: $(ls "$KS/enclaves" 2>/dev/null | tr '\n' ' ')"

echo "== [Case A] legit: secured publisher + authorized maintenance listener =="
ros2 run demo_nodes_cpp talker --ros-args \
  --enclave /diag_publisher -r __node:=diag_publisher -r chatter:=$TOPIC >/dev/null 2>&1 &
PUB=$!
ros2 run demo_nodes_cpp listener --ros-args \
  --enclave /maintenance_listener -r __node:=maintenance_listener -r chatter:=$TOPIC > "$OUT/legit.log" 2>&1 &
LIS=$!
sleep $RUN; kill $PUB $LIS 2>/dev/null; wait 2>/dev/null
LEGIT_HEARD=$(grep -c "I heard" "$OUT/legit.log")
echo "  authorized listener heard: $LEGIT_HEARD msgs"

echo "== [Case B] forbidden: unauthorized listener (no creds) on secured domain =="
ros2 run demo_nodes_cpp talker --ros-args \
  --enclave /diag_publisher -r __node:=diag_publisher -r chatter:=$TOPIC >/dev/null 2>&1 &
PUB2=$!
# unauthorized: security DISABLED -> non-secure participant, rejected by the secured domain
env ROS_SECURITY_ENABLE=false ROS_SECURITY_STRATEGY=Permissive \
  ros2 run demo_nodes_cpp listener --ros-args -r __node:=attacker -r chatter:=$TOPIC > "$OUT/attacker.log" 2>&1 &
ATK=$!
sleep $RUN; kill $PUB2 $ATK 2>/dev/null; wait 2>/dev/null
ATK_HEARD=$(grep -c "I heard" "$OUT/attacker.log")
echo "  unauthorized listener heard: $ATK_HEARD msgs"

echo "== RESULT =="
if [ "$LEGIT_HEARD" -gt 0 ] && [ "$ATK_HEARD" -eq 0 ]; then
  echo "PASS ✅  legit comms succeed ($LEGIT_HEARD) · unauthorized denied ($ATK_HEARD)"
  rm -rf "$OUT"; exit 0
else
  echo "FAIL ❌  legit=$LEGIT_HEARD (want >0) · attacker=$ATK_HEARD (want 0)"
  echo "  logs kept at $OUT"; exit 1
fi
