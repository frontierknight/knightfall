#!/usr/bin/env bash
# E1 acceptance (DESIGN §13.7): cross-container ROS 2 discovery works, and the player
# container has no network path to the judge container or the internet.
# Needs the `knightfall` image. Exit 0 = PASS.
set -uo pipefail
cd "$(dirname "$0")"
C="docker compose -f docker-compose.yml"
fail=0
check() { if eval "$2"; then echo "  PASS  $1"; else echo "  FAIL  $1"; fail=1; fi; }

$C up -d >/dev/null 2>&1 || { echo "compose up failed"; exit 1; }
trap '$C down -t 2 >/dev/null 2>&1' EXIT
sleep 8
PX="$C exec -T player bash -lc"
JIP=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "$($C ps -q judge)")

echo "== E1 checks =="
check "player discovers robot topics" \
  "$PX 'source /opt/ros/humble/setup.bash; ros2 topic list --no-daemon' | grep -q '^/localization/pose$'"
check "player receives robot data" \
  "$PX 'source /opt/ros/humble/setup.bash; timeout 10 ros2 topic echo /localization/pose --once --no-daemon' | grep -q position"
check "player cannot resolve judge" \
  "! $PX 'getent hosts judge' >/dev/null 2>&1"
check "judge canary is listening (control)" \
  "$C exec -T judge bash -lc 'timeout 3 bash -c \"echo > /dev/tcp/127.0.0.1/8080\"' >/dev/null 2>&1"
check "player cannot reach judge canary ($JIP:8080)" \
  "! $PX 'timeout 3 bash -c \"echo > /dev/tcp/$JIP/8080\"' >/dev/null 2>&1"
check "player has no internet egress" \
  "! $PX 'timeout 3 bash -c \"echo > /dev/tcp/1.1.1.1/443\"' >/dev/null 2>&1"

[ $fail -eq 0 ] && echo "E1 PASS ✅" || echo "E1 FAIL ❌"
exit $fail
