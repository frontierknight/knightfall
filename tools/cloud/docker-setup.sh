#!/usr/bin/env bash
# Bring up Docker + build the Knightfall image inside a Claude Code cloud container.
# Idempotent. Handles three cloud quirks found on 2026-09-25:
#   1. no Docker daemon running by default      -> start dockerd
#   2. Docker Hub rate-limits anonymous pulls    -> pull the ROS base from mirror.gcr.io
#   3. egress blocks packages.ros.org            -> skip the apt step (sros2 ships in ros-base;
#                                                  demo_nodes_cpp is unavailable, see below)
# Usage: bash tools/cloud/docker-setup.sh          (then: docker run --rm knightfall selftest all)
set -euo pipefail
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
WORK="$(mktemp -d)"

if ! docker info >/dev/null 2>&1; then
  (dockerd >/tmp/dockerd.log 2>&1 &)
  for _ in $(seq 1 30); do docker info >/dev/null 2>&1 && break; sleep 1; done
fi
docker info >/dev/null

docker pull -q mirror.gcr.io/library/ros:humble-ros-base
docker tag mirror.gcr.io/library/ros:humble-ros-base ros:humble-ros-base

if [ -n "${HTTPS_PROXY:-}" ]; then
  # Cloud egress blocks packages.ros.org (403), so the repo Dockerfile's apt step cannot run.
  # ros-humble-ros-base already ships sros2; ros-humble-demo-nodes-cpp is NOT available here,
  # so deliverable-01/run_acceptance.sh (task01 fix-oracle) cannot pass in this build.
  python3 - "$REPO/Dockerfile" "$WORK/Dockerfile.knightfall" <<'PY'
import re, sys
s = open(sys.argv[1]).read()
s = re.sub(r'RUN apt-get update.*?rm -rf /var/lib/apt/lists/\*\n', '', s, flags=re.S)
open(sys.argv[2], 'w').write(s)
PY
  docker build -q -f "$WORK/Dockerfile.knightfall" -t knightfall "$REPO"
else
  docker build -q -t knightfall "$REPO"
fi
rm -rf "$WORK"
echo "knightfall image ready"
